from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.settings import AppSettingsIn, AppSettingsOut
from app.services.settings import get_app_settings, upsert_app_settings


router = APIRouter()


@router.get("", response_model=AppSettingsOut)
async def get_settings(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    s = await get_app_settings(db, user.id)
    if not s:
        return AppSettingsOut(
            default_account_daily_limit=50,
            max_connections_per_day=30,
            max_messages_per_day=60,
            max_profile_visits_per_day=80,
            delay_min_ms=400,
            delay_max_ms=1600,
            proxy_url=None,
            proxy_username=None,
            proxy_password_set=False,
            work_start_min_hour=8,
            work_start_max_hour=11,
            work_end_min_hour=16,
            work_end_max_hour=21,
            campaign_timezone="UTC",
            campaign_work_days=[],
            campaign_start_hour=9,
            campaign_end_hour=17,
            blacklist_domains=[],
            blacklist_linkedin_urls=[],
        )
    return AppSettingsOut(
        default_account_daily_limit=int(s.default_account_daily_limit),
        max_connections_per_day=int(s.max_connections_per_day),
        max_messages_per_day=int(s.max_messages_per_day),
        max_profile_visits_per_day=int(s.max_profile_visits_per_day),
        delay_min_ms=int(s.delay_min_ms),
        delay_max_ms=int(s.delay_max_ms),
        proxy_url=s.proxy_url,
        proxy_username=s.proxy_username,
        proxy_password_set=bool(s.proxy_password),
        work_start_min_hour=int(s.work_start_min_hour),
        work_start_max_hour=int(s.work_start_max_hour),
        work_end_min_hour=int(s.work_end_min_hour),
        work_end_max_hour=int(s.work_end_max_hour),
        campaign_timezone=s.campaign_timezone,
        campaign_work_days=list(s.campaign_work_days or []),
        campaign_start_hour=int(s.campaign_start_hour),
        campaign_end_hour=int(s.campaign_end_hour),
        blacklist_domains=list(s.blacklist_domains or []),
        blacklist_linkedin_urls=list(s.blacklist_linkedin_urls or []),
    )


@router.put("", response_model=AppSettingsOut)
async def put_settings(
    payload: AppSettingsIn,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    updates = payload.model_dump(exclude_unset=True)
    s = await upsert_app_settings(db, user_id=user.id, updates=updates)
    return AppSettingsOut(
        default_account_daily_limit=int(s.default_account_daily_limit),
        max_connections_per_day=int(s.max_connections_per_day),
        max_messages_per_day=int(s.max_messages_per_day),
        max_profile_visits_per_day=int(s.max_profile_visits_per_day),
        delay_min_ms=int(s.delay_min_ms),
        delay_max_ms=int(s.delay_max_ms),
        proxy_url=s.proxy_url,
        proxy_username=s.proxy_username,
        proxy_password_set=bool(s.proxy_password),
        work_start_min_hour=int(s.work_start_min_hour),
        work_start_max_hour=int(s.work_start_max_hour),
        work_end_min_hour=int(s.work_end_min_hour),
        work_end_max_hour=int(s.work_end_max_hour),
        campaign_timezone=s.campaign_timezone,
        campaign_work_days=list(s.campaign_work_days or []),
        campaign_start_hour=int(s.campaign_start_hour),
        campaign_end_hour=int(s.campaign_end_hour),
        blacklist_domains=list(s.blacklist_domains or []),
        blacklist_linkedin_urls=list(s.blacklist_linkedin_urls or []),
    )

