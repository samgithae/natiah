import json
import logging
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.api.deps import get_current_user
from app.db.session import async_session_maker, get_db
from app.schemas.linkedin_account import (
    LinkedInAccountCreate,
    LinkedInAccountOut,
    LinkedInAccountUpdate,
)
from app.schemas.linkedin_connect import ConnectCompleteIn, ConnectLinkOut, ConnectStatusOut
from app.services.account_service import create_linkedin_account, get_linkedin_account, list_linkedin_accounts
from app.services.linkedin_accounts import delete_account, update_account
from app.services.linkedin_oauth_service import generate_pkce_pair
from app.services.linkedin_session_service import (
    connect_with_li_at_cookie,
    create_connect_token,
    decode_connect_token,
    open_and_verify,
    wait_for_manual_login,
)
from app.services.playwright_manager import close_persistent_context, launch_persistent_context


router = APIRouter()


@router.get("", response_model=list[LinkedInAccountOut])
async def get_accounts(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    accounts = await list_linkedin_accounts(db, user_id=user.id)
    return [
        LinkedInAccountOut(
            id=a.id,
            name=a.name,
            linkedin_email=a.linkedin_email,
            session_path=a.session_path,
            daily_limit=a.daily_limit,
            status=a.status,
            last_connected_at=a.last_connected_at,
            created_at=a.created_at,
            li_member_id=a.li_member_id,
            li_token_expires_at=a.li_token_expires_at,
        )
        for a in accounts
    ]


@router.post("", response_model=LinkedInAccountOut, status_code=status.HTTP_201_CREATED)
async def create_new_account(
    payload: LinkedInAccountCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    a = await create_linkedin_account(
        db,
        user_id=user.id,
        name=payload.name,
        linkedin_email=payload.linkedin_email,
        daily_limit=payload.daily_limit,
    )
    return LinkedInAccountOut(
        id=a.id,
        name=a.name,
        linkedin_email=a.linkedin_email,
        session_path=a.session_path,
        daily_limit=a.daily_limit,
        status=a.status,
        last_connected_at=a.last_connected_at,
        created_at=a.created_at,
        li_member_id=a.li_member_id,
        li_token_expires_at=a.li_token_expires_at,
    )


@router.put("/{account_id}", response_model=LinkedInAccountOut)
async def update_existing_account(
    account_id: uuid.UUID,
    payload: LinkedInAccountUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    a = await update_account(
        db,
        user.id,
        account_id,
        name=payload.name,
        linkedin_email=payload.linkedin_email,
        daily_limit=payload.daily_limit,
        status=payload.status,
        last_active=None,
    )
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return LinkedInAccountOut(
        id=a.id,
        name=a.name,
        linkedin_email=a.linkedin_email,
        session_path=a.session_path,
        daily_limit=a.daily_limit,
        status=a.status,
        last_connected_at=a.last_connected_at,
        created_at=a.created_at,
        li_member_id=a.li_member_id,
        li_token_expires_at=a.li_token_expires_at,
    )


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_account(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    ok = await delete_account(db, user.id, account_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return None


@router.get("/{account_id}", response_model=LinkedInAccountOut)
async def get_one_account(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    a = await get_linkedin_account(db, user_id=user.id, account_id=account_id)
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return LinkedInAccountOut(
        id=a.id,
        name=a.name,
        linkedin_email=a.linkedin_email,
        session_path=a.session_path,
        daily_limit=a.daily_limit,
        status=a.status,
        last_connected_at=a.last_connected_at,
        created_at=a.created_at,
        li_member_id=a.li_member_id,
        li_token_expires_at=a.li_token_expires_at,
    )


@router.post("/{account_id}/connect")
async def connect_linkedin(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    a = await get_linkedin_account(db, user_id=user.id, account_id=account_id)
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if not a.session_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing session profile path")

    ctx = await launch_persistent_context(
        user_data_dir=a.session_path,
        headless=False,
        slow_mo_ms=35,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-infobars",
            "--disable-notifications",
        ],
    )
    try:
        res = await wait_for_manual_login(ctx.context, ctx.page, timeout_s=360)
        a.status = res.status
        if res.status == "connected":
            a.last_connected_at = datetime.now(timezone.utc)
        await db.commit()
        return {"status": a.status}
    except Exception as e:
        a.status = "expired"
        await db.commit()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        await close_persistent_context(ctx.context)


@router.post("/{account_id}/connect-link", response_model=ConnectLinkOut)
async def connect_link(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    a = await get_linkedin_account(db, user_id=user.id, account_id=account_id)
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    token = create_connect_token(user_id=str(user.id), account_id=str(a.id), expires_minutes=30)
    url = f"http://localhost:3000/connect/linkedin?token={token}"
    return ConnectLinkOut(url=url)


class OAuthInitiateOut(BaseModel):
    connect_url: str


@router.post("/{account_id}/oauth/init", response_model=OAuthInitiateOut)
async def oauth_initiate(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    if not settings.linkedin_client_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="LinkedIn OAuth not configured: LINKEDIN_CLIENT_ID is not set")

    a = await get_linkedin_account(db, user_id=user.id, account_id=account_id)
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    code_verifier, code_challenge = generate_pkce_pair()
    state = secrets.token_urlsafe(32)

    from app.services.linkedin_oauth_service import build_authorization_url, get_linkedin_scopes

    callback_url = settings.linkedin_callback_url or "http://localhost:8000/api/v1/accounts/oauth/callback"
    if callback_url == "http://localhost:3000/connect/linkedin/callback":
        callback_url = "http://localhost:8000/api/v1/accounts/oauth/callback"
    if "{account_id}" in callback_url:
        callback_url = callback_url.replace("{account_id}/oauth/callback", "oauth/callback")

    auth_url = build_authorization_url(
        client_id=settings.linkedin_client_id,
        redirect_uri=callback_url,
        state=state,
        code_challenge=code_challenge,
        scopes=get_linkedin_scopes(),
    )

    state_dir = Path("/tmp/natiah_li_oauth")
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / f"{state}.json").write_text(
        json.dumps(
            {
                "state": state,
                "code_verifier": code_verifier,
                "account_id": str(account_id),
                "user_id": str(user.id),
            }
        )
    )

    return OAuthInitiateOut(connect_url=auth_url)


class OAuthCompleteIn(BaseModel):
    code: str
    state: str
    code_verifier: str


@router.post("/{account_id}/oauth/complete", response_model=ConnectStatusOut)
async def oauth_complete(
    account_id: uuid.UUID,
    payload: OAuthCompleteIn,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    if not settings.linkedin_client_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="LinkedIn OAuth not configured")

    a = await get_linkedin_account(db, user_id=user.id, account_id=account_id)
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    from app.services.linkedin_oauth_service import (
        exchange_code_for_token,
        fetch_linkedin_userinfo,
        token_expiry_time,
    )

    token_data = await exchange_code_for_token(
        client_id=settings.linkedin_client_id,
        client_secret=settings.linkedin_client_secret,
        code=payload.code,
        redirect_uri=(settings.linkedin_callback_url or "http://localhost:8000/api/v1/accounts/oauth/callback").replace(
            "{account_id}/oauth/callback", "oauth/callback"
        ),
        code_verifier=payload.code_verifier,
    )

    userinfo = await fetch_linkedin_userinfo(token_data.access_token)

    a.li_access_token = token_data.access_token
    a.li_refresh_token = token_data.refresh_token
    a.li_token_expires_at = token_expiry_time(token_data.expires_in)
    a.li_member_id = userinfo.get("sub") or userinfo.get("id")
    a.status = "connected"
    a.last_connected_at = datetime.now(timezone.utc)

    await db.commit()

    return ConnectStatusOut(status="connected", detail=f"LinkedIn account connected: {userinfo.get('name', 'Unknown')}")


@router.get("/oauth/callback")
async def oauth_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if error:
        return RedirectResponse(url=f"http://localhost:3000/connect/linkedin/callback?error={error}")
    if not code or not state:
        return RedirectResponse(url="http://localhost:3000/connect/linkedin/callback?error=missing_code")

    state_dir = Path("/tmp/natiah_li_oauth")
    state_file = state_dir / f"{state}.json"
    if not state_file.exists():
        return RedirectResponse(url="http://localhost:3000/connect/linkedin/callback?error=state_not_found")

    try:
        pkce_data = json.loads(state_file.read_text())
    except Exception:
        return RedirectResponse(url="http://localhost:3000/connect/linkedin/callback?error=invalid_state_file")

    if pkce_data.get("state") != state:
        return RedirectResponse(url="http://localhost:3000/connect/linkedin/callback?error=state_mismatch")

    try:
        account_id = uuid.UUID(str(pkce_data.get("account_id")))
    except Exception:
        return RedirectResponse(url="http://localhost:3000/connect/linkedin/callback?error=invalid_account")

    code_verifier = str(pkce_data.get("code_verifier") or "")
    callback_url = settings.linkedin_callback_url or "http://localhost:8000/api/v1/accounts/oauth/callback"
    if callback_url == "http://localhost:3000/connect/linkedin/callback":
        callback_url = "http://localhost:8000/api/v1/accounts/oauth/callback"
    if "{account_id}" in callback_url:
        callback_url = callback_url.replace("{account_id}/oauth/callback", "oauth/callback")

    async with async_session_maker() as db:
        from sqlalchemy import select
        from app.models.linkedin_account import LinkedInAccount

        res = await db.execute(select(LinkedInAccount).where(LinkedInAccount.id == account_id))
        a = res.scalar_one_or_none()
        if not a:
            return RedirectResponse(
                url=f"http://localhost:3000/connect/linkedin/callback?error=account_not_found&account_id={account_id}"
            )

        from app.services.linkedin_oauth_service import exchange_code_for_token, fetch_linkedin_userinfo, token_expiry_time

        try:
            token_data = await exchange_code_for_token(
                client_id=settings.linkedin_client_id,
                client_secret=settings.linkedin_client_secret,
                code=code,
                redirect_uri=callback_url,
                code_verifier=code_verifier or None,
            )
        except Exception as e:
            logging.getLogger("natiah").exception("LinkedIn token exchange failed")
            if code_verifier:
                try:
                    token_data = await exchange_code_for_token(
                        client_id=settings.linkedin_client_id,
                        client_secret=settings.linkedin_client_secret,
                        code=code,
                        redirect_uri=callback_url,
                        code_verifier=None,
                    )
                except Exception:
                    msg = str(e)
                    if "unauthorized_scope_error" in msg:
                        return RedirectResponse(url="http://localhost:3000/connect/linkedin/callback?error=unauthorized_scope")
                    if "redirect_uri" in msg or "redirect" in msg:
                        return RedirectResponse(url="http://localhost:3000/connect/linkedin/callback?error=invalid_redirect_uri")
                    if "invalid_client" in msg or "client_secret" in msg:
                        return RedirectResponse(url="http://localhost:3000/connect/linkedin/callback?error=invalid_client")
                    return RedirectResponse(url="http://localhost:3000/connect/linkedin/callback?error=token_exchange_failed")
            else:
                msg = str(e)
                if "unauthorized_scope_error" in msg:
                    return RedirectResponse(url="http://localhost:3000/connect/linkedin/callback?error=unauthorized_scope")
                if "redirect_uri" in msg or "redirect" in msg:
                    return RedirectResponse(url="http://localhost:3000/connect/linkedin/callback?error=invalid_redirect_uri")
                if "invalid_client" in msg or "client_secret" in msg:
                    return RedirectResponse(url="http://localhost:3000/connect/linkedin/callback?error=invalid_client")
                return RedirectResponse(url="http://localhost:3000/connect/linkedin/callback?error=token_exchange_failed")

        try:
            userinfo = await fetch_linkedin_userinfo(token_data.access_token)
        except Exception:
            logging.getLogger("natiah").exception("LinkedIn userinfo failed")
            return RedirectResponse(url="http://localhost:3000/connect/linkedin/callback?error=userinfo_failed")

        a.li_access_token = token_data.access_token
        a.li_refresh_token = token_data.refresh_token
        a.li_token_expires_at = token_expiry_time(token_data.expires_in)
        a.li_member_id = userinfo.get("sub") or userinfo.get("id")
        a.status = "connected"
        a.last_connected_at = datetime.now(timezone.utc)
        await db.commit()

    state_file.unlink(missing_ok=True)

    member_name = userinfo.get("name", "Account")
    return RedirectResponse(
        url=f"http://localhost:3000/connect/linkedin/callback?success=1&account_id={account_id}&name={member_name}"
    )


@router.get("/{account_id}/oauth/callback")
async def oauth_callback_legacy(account_id: uuid.UUID, code: str | None = None, state: str | None = None, error: str | None = None):
    qs = []
    if code is not None:
        qs.append(f"code={code}")
    if state is not None:
        qs.append(f"state={state}")
    if error is not None:
        qs.append(f"error={error}")
    q = "&".join(qs)
    return RedirectResponse(url=f"http://localhost:8000/api/v1/accounts/oauth/callback{('?' + q) if q else ''}")


@router.post("/connect/complete", response_model=ConnectStatusOut)
async def connect_complete(
    payload: ConnectCompleteIn,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        data = decode_connect_token(payload.token)
        if str(data.get("sub")) != str(user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")
        account_id = uuid.UUID(str(data.get("acc")))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")

    a = await get_linkedin_account(db, user_id=user.id, account_id=account_id)
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if not a.session_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing session profile path")

    ctx = await launch_persistent_context(
        user_data_dir=a.session_path,
        headless=True,
        slow_mo_ms=0,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-infobars",
            "--disable-notifications",
        ],
    )
    try:
        res = await connect_with_li_at_cookie(context=ctx.context, page=ctx.page, li_at=payload.li_at)
        a.status = res.status
        if res.status == "connected":
            a.last_connected_at = datetime.now(timezone.utc)
        await db.commit()
        return ConnectStatusOut(status=a.status, detail=res.detail)
    finally:
        await close_persistent_context(ctx.context)


@router.get("/{account_id}/verify")
async def verify_linkedin(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    a = await get_linkedin_account(db, user_id=user.id, account_id=account_id)
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if not a.session_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing session profile path")

    ctx = await launch_persistent_context(
        user_data_dir=a.session_path,
        headless=True,
        slow_mo_ms=0,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-infobars",
            "--disable-notifications",
        ],
    )
    try:
        chk = await open_and_verify(ctx.context, ctx.page)
        a.status = chk.status
        await db.commit()
        return {"status": a.status}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        await close_persistent_context(ctx.context)


@router.post("/{account_id}/reconnect")
async def reconnect_linkedin(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    a = await get_linkedin_account(db, user_id=user.id, account_id=account_id)
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if not a.session_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing session profile path")

    a.status = "pending"
    await db.commit()

    ctx = await launch_persistent_context(
        user_data_dir=a.session_path,
        headless=False,
        slow_mo_ms=35,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-infobars",
            "--disable-notifications",
        ],
    )
    try:
        res = await wait_for_manual_login(ctx.context, ctx.page, timeout_s=360)
        a.status = res.status
        if res.status == "connected":
            a.last_connected_at = datetime.now(timezone.utc)
        await db.commit()
        return {"status": a.status}
    except Exception as e:
        a.status = "expired"
        await db.commit()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        await close_persistent_context(ctx.context)
