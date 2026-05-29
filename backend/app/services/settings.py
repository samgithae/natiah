import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_settings import AppSettings


def _clamp_int(v: int, *, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(v)))


async def get_app_settings(db: AsyncSession, user_id: uuid.UUID) -> AppSettings | None:
    res = await db.execute(select(AppSettings).where(AppSettings.user_id == user_id))
    return res.scalar_one_or_none()


async def upsert_app_settings(db: AsyncSession, *, user_id: uuid.UUID, updates: dict) -> AppSettings:
    s = await get_app_settings(db, user_id)
    if not s:
        s = AppSettings(user_id=user_id)
        db.add(s)
        await db.commit()
        await db.refresh(s)

    if "default_account_daily_limit" in updates and updates["default_account_daily_limit"] is not None:
        s.default_account_daily_limit = _clamp_int(updates["default_account_daily_limit"], lo=1, hi=10000)

    if "max_connections_per_day" in updates and updates["max_connections_per_day"] is not None:
        s.max_connections_per_day = _clamp_int(updates["max_connections_per_day"], lo=0, hi=1000)
    if "max_messages_per_day" in updates and updates["max_messages_per_day"] is not None:
        s.max_messages_per_day = _clamp_int(updates["max_messages_per_day"], lo=0, hi=5000)
    if "max_profile_visits_per_day" in updates and updates["max_profile_visits_per_day"] is not None:
        s.max_profile_visits_per_day = _clamp_int(updates["max_profile_visits_per_day"], lo=0, hi=10000)

    if "delay_min_ms" in updates and updates["delay_min_ms"] is not None:
        s.delay_min_ms = _clamp_int(updates["delay_min_ms"], lo=0, hi=600000)
    if "delay_max_ms" in updates and updates["delay_max_ms"] is not None:
        s.delay_max_ms = _clamp_int(updates["delay_max_ms"], lo=0, hi=600000)
    if s.delay_max_ms < s.delay_min_ms:
        s.delay_max_ms = s.delay_min_ms

    if "proxy_url" in updates:
        s.proxy_url = (updates.get("proxy_url") or None) if updates.get("proxy_url") is not None else s.proxy_url
    if "proxy_username" in updates:
        s.proxy_username = (updates.get("proxy_username") or None) if updates.get("proxy_username") is not None else s.proxy_username
    if "proxy_password" in updates:
        val = updates.get("proxy_password")
        if val is not None:
            s.proxy_password = val or None

    for k in ("work_start_min_hour", "work_start_max_hour", "work_end_min_hour", "work_end_max_hour"):
        if k in updates and updates[k] is not None:
            setattr(s, k, _clamp_int(updates[k], lo=0, hi=23))

    if "campaign_timezone" in updates and updates["campaign_timezone"] is not None:
        s.campaign_timezone = updates["campaign_timezone"] or "UTC"
    if "campaign_work_days" in updates and updates["campaign_work_days"] is not None:
        days = [int(x) for x in updates["campaign_work_days"] if isinstance(x, int) or str(x).isdigit()]
        s.campaign_work_days = [d for d in days if 0 <= d <= 6]
    if "campaign_start_hour" in updates and updates["campaign_start_hour"] is not None:
        s.campaign_start_hour = _clamp_int(updates["campaign_start_hour"], lo=0, hi=23)
    if "campaign_end_hour" in updates and updates["campaign_end_hour"] is not None:
        s.campaign_end_hour = _clamp_int(updates["campaign_end_hour"], lo=0, hi=23)

    if "blacklist_domains" in updates and updates["blacklist_domains"] is not None:
        s.blacklist_domains = [str(x).strip().lower() for x in updates["blacklist_domains"] if str(x).strip()]
    if "blacklist_linkedin_urls" in updates and updates["blacklist_linkedin_urls"] is not None:
        s.blacklist_linkedin_urls = [str(x).strip() for x in updates["blacklist_linkedin_urls"] if str(x).strip()]

    await db.commit()
    await db.refresh(s)
    return s

