from __future__ import annotations

import os
from datetime import datetime, timezone

from sqlalchemy import and_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401
from app.models.automation_job import AutomationJob
from app.models.linkedin_account import LinkedInAccount
from app.models.user import User


def worker_id() -> str:
    return os.environ.get("NATIAH_WORKER_ID") or os.uname().nodename


async def fetch_and_lock_next_job(db: AsyncSession) -> AutomationJob | None:
    now = datetime.now(timezone.utc)
    stmt = (
        select(AutomationJob)
        .where(
            and_(
                AutomationJob.status == "queued",
                AutomationJob.run_at <= now,
            )
        )
        .order_by(AutomationJob.run_at.asc(), AutomationJob.created_at.asc())
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()
    if not job:
        return None

    job.status = "running"
    job.locked_at = now
    job.locked_by = worker_id()
    job.attempts = int(job.attempts or 0) + 1
    await db.commit()
    await db.refresh(job)
    return job


async def mark_job_done(db: AsyncSession, job_id) -> None:
    await db.execute(
        update(AutomationJob)
        .where(AutomationJob.id == job_id)
        .values(status="done", locked_at=None, locked_by=None, last_error=None, updated_at=text("now()"))
    )
    await db.commit()


async def mark_job_failed(db: AsyncSession, job_id, error: str) -> None:
    await db.execute(
        update(AutomationJob)
        .where(AutomationJob.id == job_id)
        .values(status="failed", last_error=error[:2000], updated_at=text("now()"))
    )
    await db.commit()


async def reschedule_job(db: AsyncSession, job_id, run_at: datetime, reason: str | None = None) -> None:
    await db.execute(
        update(AutomationJob)
        .where(AutomationJob.id == job_id)
        .values(
            status="queued",
            run_at=run_at,
            locked_at=None,
            locked_by=None,
            last_error=(reason or None),
            updated_at=text("now()"),
        )
    )
    await db.commit()
