import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.automation_job import AutomationJob


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def enqueue_automation_job(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    job_type: str,
    payload: dict,
    run_at: datetime | None = None,
) -> AutomationJob:
    job = AutomationJob(
        user_id=user_id,
        account_id=account_id,
        job_type=job_type,
        payload=payload or {},
        status="queued",
        run_at=run_at or _utc_now(),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job
