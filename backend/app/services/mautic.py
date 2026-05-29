import uuid
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead
from app.models.mautic_settings import MauticSettings


def _base_url(url: str) -> str:
    return url.rstrip("/")


def _auth_headers(settings: MauticSettings) -> dict[str, str]:
    if settings.api_token:
        return {"Authorization": f"Bearer {settings.api_token}"}
    return {}


def _auth_basic(settings: MauticSettings) -> tuple[str, str] | None:
    if settings.api_token:
        return None
    if settings.username and settings.password:
        return (settings.username, settings.password)
    return None


async def get_settings(db: AsyncSession, user_id: uuid.UUID) -> MauticSettings | None:
    res = await db.execute(select(MauticSettings).where(MauticSettings.user_id == user_id))
    return res.scalar_one_or_none()


async def upsert_settings(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    mautic_url: str,
    username: str | None,
    password,
    api_token,
) -> MauticSettings:
    existing = await get_settings(db, user_id)
    if existing:
        existing.mautic_url = mautic_url
        existing.username = username
        if password is not UNSET:
            existing.password = password
        if api_token is not UNSET:
            existing.api_token = api_token
        await db.commit()
        await db.refresh(existing)
        return existing

    s = MauticSettings(
        user_id=user_id,
        mautic_url=mautic_url,
        username=username,
        password=(password if password is not UNSET else None),
        api_token=(api_token if api_token is not UNSET else None),
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


class _Unset:
    pass


UNSET = _Unset()


async def _search_contact(
    client: httpx.AsyncClient,
    base_url: str,
    *,
    email: str | None,
    linkedin_url: str | None,
) -> int | None:
    if not email and not linkedin_url:
        return None
    q = email or linkedin_url or ""
    resp = await client.get(f"{base_url}/api/contacts", params={"search": q})
    resp.raise_for_status()
    data = resp.json()
    contacts = data.get("contacts") or {}
    if not isinstance(contacts, dict) or not contacts:
        return None
    first = next(iter(contacts.keys()), None)
    return int(first) if first is not None else None


async def create_or_update_contact(
    client: httpx.AsyncClient,
    base_url: str,
    *,
    lead: Lead,
) -> int:
    contact_data: dict[str, Any] = {}
    if lead.email:
        contact_data["email"] = lead.email
    if lead.first_name:
        contact_data["firstname"] = lead.first_name
    if lead.last_name:
        contact_data["lastname"] = lead.last_name
    if lead.company:
        contact_data["company"] = lead.company
    if lead.job_title:
        contact_data["position"] = lead.job_title
    contact_data["linkedin_url"] = lead.linkedin_url

    existing_id = await _search_contact(client, base_url, email=lead.email, linkedin_url=lead.linkedin_url)
    if existing_id:
        resp = await client.patch(f"{base_url}/api/contacts/{existing_id}/edit", json=contact_data)
        resp.raise_for_status()
        return existing_id

    resp = await client.post(f"{base_url}/api/contacts/new", json=contact_data)
    resp.raise_for_status()
    out = resp.json()
    contact = out.get("contact") or {}
    contact_id = contact.get("id")
    if not contact_id:
        raise RuntimeError("Mautic did not return contact id")
    return int(contact_id)


async def add_tags(client: httpx.AsyncClient, base_url: str, *, contact_id: int, tags: list[str]) -> None:
    for tag in tags:
        t = (tag or "").strip()
        if not t:
            continue
        resp = await client.post(f"{base_url}/api/contacts/{contact_id}/tags/add/{t}")
        if resp.status_code >= 400:
            resp.raise_for_status()


async def add_to_segments(
    client: httpx.AsyncClient, base_url: str, *, contact_id: int, segment_ids: list[int]
) -> None:
    for seg_id in segment_ids:
        resp = await client.post(f"{base_url}/api/segments/{int(seg_id)}/contact/{contact_id}/add")
        if resp.status_code >= 400:
            resp.raise_for_status()


async def bulk_sync(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    lead_ids: list[uuid.UUID],
    tags: list[str],
    segment_ids: list[int],
) -> dict:
    settings = await get_settings(db, user_id)
    if not settings:
        raise RuntimeError("Mautic settings not configured")

    leads_res = await db.execute(select(Lead).where(Lead.id.in_(lead_ids)))
    leads = list(leads_res.scalars().all())

    base_url = _base_url(settings.mautic_url)
    headers = _auth_headers(settings)
    auth = _auth_basic(settings)
    timeout = httpx.Timeout(30.0, connect=20.0)
    results: list[dict[str, Any]] = []

    async with httpx.AsyncClient(headers=headers, auth=auth, timeout=timeout) as client:
        for lead in leads:
            try:
                contact_id = await create_or_update_contact(client, base_url, lead=lead)
                if tags:
                    await add_tags(client, base_url, contact_id=contact_id, tags=tags)
                if segment_ids:
                    await add_to_segments(client, base_url, contact_id=contact_id, segment_ids=segment_ids)
                results.append({"lead_id": str(lead.id), "status": "ok", "contact_id": contact_id})
            except Exception as e:
                results.append({"lead_id": str(lead.id), "status": "error", "error": f"{type(e).__name__}: {e}"})

    ok = sum(1 for r in results if r["status"] == "ok")
    return {"ok": ok, "failed": len(results) - ok, "results": results}
