import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.linkedin_account import LinkedInAccount


async def list_accounts(db: AsyncSession, user_id: uuid.UUID) -> list[LinkedInAccount]:
    res = await db.execute(select(LinkedInAccount).where(LinkedInAccount.user_id == user_id))
    return list(res.scalars().all())


async def create_account(
    db: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    linkedin_email: str | None,
    daily_limit: int,
) -> LinkedInAccount:
    acc = LinkedInAccount(
        user_id=user_id,
        name=name,
        linkedin_email=linkedin_email,
        daily_limit=daily_limit,
        status="pending",
    )
    db.add(acc)
    await db.commit()
    await db.refresh(acc)
    return acc


async def get_account(db: AsyncSession, user_id: uuid.UUID, account_id: uuid.UUID) -> LinkedInAccount | None:
    res = await db.execute(
        select(LinkedInAccount).where(LinkedInAccount.user_id == user_id, LinkedInAccount.id == account_id)
    )
    return res.scalar_one_or_none()


async def update_account(
    db: AsyncSession,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    *,
    name: str | None,
    linkedin_email: str | None,
    session_path: str | None = None,
    daily_limit: int | None,
    status: str | None,
    last_active: datetime | None = None,
) -> LinkedInAccount | None:
    acc = await get_account(db, user_id, account_id)
    if not acc:
        return None
    if name is not None:
        acc.name = name
    if linkedin_email is not None:
        acc.linkedin_email = linkedin_email
    if session_path is not None:
        acc.session_path = session_path
    if daily_limit is not None:
        acc.daily_limit = daily_limit
    if status is not None:
        acc.status = status
    if last_active is not None:
        acc.last_active = last_active
    await db.commit()
    await db.refresh(acc)
    return acc


async def delete_account(db: AsyncSession, user_id: uuid.UUID, account_id: uuid.UUID) -> bool:
    res = await db.execute(
        delete(LinkedInAccount).where(LinkedInAccount.user_id == user_id, LinkedInAccount.id == account_id)
    )
    await db.commit()
    return res.rowcount > 0
