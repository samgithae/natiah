import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.linkedin_account import LinkedInAccount


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def profile_dir_for_account_id(account_id: uuid.UUID) -> Path:
    base = _project_root() / "automation" / "profiles"
    suffix = str(account_id).replace("-", "")[:8]
    return base / f"account_{suffix}"


async def create_linkedin_account(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    name: str,
    linkedin_email: str | None,
    daily_limit: int,
) -> LinkedInAccount:
    acc = LinkedInAccount(
        id=uuid.uuid4(),
        user_id=user_id,
        name=name,
        linkedin_email=linkedin_email,
        daily_limit=daily_limit,
        status="pending",
    )

    profile_dir = profile_dir_for_account_id(acc.id)
    profile_dir.mkdir(parents=True, exist_ok=True)
    acc.session_path = str(profile_dir)

    db.add(acc)
    await db.commit()
    await db.refresh(acc)
    return acc


async def get_linkedin_account(db: AsyncSession, *, user_id: uuid.UUID, account_id: uuid.UUID) -> LinkedInAccount | None:
    res = await db.execute(
        select(LinkedInAccount).where(LinkedInAccount.user_id == user_id, LinkedInAccount.id == account_id)
    )
    return res.scalar_one_or_none()


async def list_linkedin_accounts(db: AsyncSession, *, user_id: uuid.UUID) -> list[LinkedInAccount]:
    res = await db.execute(select(LinkedInAccount).where(LinkedInAccount.user_id == user_id))
    return list(res.scalars().all())
