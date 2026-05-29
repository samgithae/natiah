import uuid

from celery import Celery
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.campaign import Campaign


celery_client = Celery("natiah_api", broker=settings.redis_url, backend=settings.redis_url)


async def list_campaigns(db: AsyncSession, user_id: uuid.UUID) -> list[Campaign]:
    res = await db.execute(select(Campaign).where(Campaign.user_id == user_id).order_by(Campaign.created_at.desc()))
    return list(res.scalars().all())


async def create_campaign(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    name: str,
    daily_limit: int,
) -> Campaign:
    c = Campaign(user_id=user_id, name=name, daily_limit=daily_limit, status="draft")
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


async def get_campaign(db: AsyncSession, user_id: uuid.UUID, campaign_id: uuid.UUID) -> Campaign | None:
    res = await db.execute(select(Campaign).where(Campaign.user_id == user_id, Campaign.id == campaign_id))
    return res.scalar_one_or_none()


async def update_campaign(
    db: AsyncSession,
    user_id: uuid.UUID,
    campaign_id: uuid.UUID,
    *,
    name: str | None,
    status: str | None,
    daily_limit: int | None,
) -> Campaign | None:
    c = await get_campaign(db, user_id, campaign_id)
    if not c:
        return None
    if name is not None:
        c.name = name
    if status is not None:
        c.status = status
    if daily_limit is not None:
        c.daily_limit = daily_limit
    await db.commit()
    await db.refresh(c)
    return c


async def delete_campaign(db: AsyncSession, user_id: uuid.UUID, campaign_id: uuid.UUID) -> bool:
    res = await db.execute(delete(Campaign).where(Campaign.user_id == user_id, Campaign.id == campaign_id))
    await db.commit()
    return res.rowcount > 0


async def start_campaign(db: AsyncSession, user_id: uuid.UUID, campaign_id: uuid.UUID) -> bool:
    c = await get_campaign(db, user_id, campaign_id)
    if not c:
        return False
    c.status = "running"
    await db.commit()
    celery_client.send_task("workers.tasks.run_campaign", args=[str(c.id), str(user_id)])
    return True


async def stop_campaign(db: AsyncSession, user_id: uuid.UUID, campaign_id: uuid.UUID) -> bool:
    c = await get_campaign(db, user_id, campaign_id)
    if not c:
        return False
    c.status = "stopped"
    await db.commit()
    return True
