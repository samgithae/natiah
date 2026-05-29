from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.mautic import MauticSettingsIn, MauticSettingsOut, MauticSyncRequest
from app.services.campaigns import celery_client
from app.services.mautic import UNSET, get_settings, upsert_settings


router = APIRouter()


@router.get("/settings", response_model=MauticSettingsOut)
async def get_mautic_settings(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    s = await get_settings(db, user.id)
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not configured")
    return MauticSettingsOut(
        mautic_url=s.mautic_url,
        username=s.username,
        password_set=bool(s.password),
        api_token_set=bool(s.api_token),
    )


@router.post("/sync")
async def sync_leads_to_mautic(payload: MauticSyncRequest, user=Depends(get_current_user)):
    task = celery_client.send_task(
        "workers.tasks.sync_mautic",
        args=[user.id.hex, payload.lead_ids, payload.tags, payload.segment_ids],
    )
    return {"task_id": task.id}


@router.put("/settings", response_model=MauticSettingsOut)
async def put_mautic_settings(
    payload: MauticSettingsIn,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    data = payload.model_dump(exclude_unset=True)
    s = await upsert_settings(
        db,
        user_id=user.id,
        mautic_url=payload.mautic_url,
        username=payload.username,
        password=data.get("password", UNSET),
        api_token=data.get("api_token", UNSET),
    )
    return MauticSettingsOut(
        mautic_url=s.mautic_url,
        username=s.username,
        password_set=bool(s.password),
        api_token_set=bool(s.api_token),
    )
