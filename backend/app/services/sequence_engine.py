import uuid
from datetime import datetime, timedelta, timezone

from celery import Celery
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.lead import Lead
from app.models.sequence import MessageSequence
from app.models.sequence_action import SequenceAction
from app.models.sequence_enrollment import SequenceEnrollment


celery_client = Celery("natiah_sequence_engine", broker=settings.redis_url, backend=settings.redis_url)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def enroll_lead_in_campaign(db: AsyncSession, *, campaign_id: uuid.UUID, lead_id: uuid.UUID) -> SequenceEnrollment:
    stmt = (
        insert(SequenceEnrollment)
        .values(campaign_id=campaign_id, lead_id=lead_id, status="active")
        .on_conflict_do_nothing(constraint="uq_enrollment_campaign_lead")
        .returning(SequenceEnrollment.id)
    )
    res = await db.execute(stmt)
    enrollment_id = res.scalar_one_or_none()
    await db.commit()
    if enrollment_id:
        enr_res = await db.execute(select(SequenceEnrollment).where(SequenceEnrollment.id == enrollment_id))
        return enr_res.scalar_one()
    enr_res = await db.execute(
        select(SequenceEnrollment).where(
            SequenceEnrollment.campaign_id == campaign_id, SequenceEnrollment.lead_id == lead_id
        )
    )
    return enr_res.scalar_one()


async def schedule_sequence_actions(db: AsyncSession, *, enrollment: SequenceEnrollment) -> int:
    seq_res = await db.execute(
        select(MessageSequence)
        .where(MessageSequence.campaign_id == enrollment.campaign_id)
        .order_by(MessageSequence.step_number.asc())
    )
    steps = list(seq_res.scalars().all())
    if not steps:
        return 0

    base = _utc_now()
    created = 0
    for step in steps:
        scheduled_at = base + timedelta(days=int(step.delay_days or 0))
        stmt = (
            insert(SequenceAction)
            .values(
                enrollment_id=enrollment.id,
                campaign_id=enrollment.campaign_id,
                lead_id=enrollment.lead_id,
                action_type=step.action_type,
                step_number=step.step_number,
                scheduled_at=scheduled_at,
                status="queued",
                payload={"template": step.message_template, "email_subject": step.email_subject},
            )
            .on_conflict_do_nothing(constraint="uq_action_enrollment_step")
            .returning(SequenceAction.id)
        )
        res = await db.execute(stmt)
        if res.scalar_one_or_none():
            created += 1
    await db.commit()
    return created


async def dispatch_due_actions(db: AsyncSession, *, limit: int = 100) -> int:
    now = _utc_now()
    res = await db.execute(
        select(SequenceAction)
        .where(SequenceAction.status == "queued", SequenceAction.scheduled_at <= now)
        .order_by(SequenceAction.scheduled_at.asc())
        .limit(limit)
    )
    actions = list(res.scalars().all())
    for a in actions:
        a.status = "running"
    await db.commit()

    for a in actions:
        celery_client.send_task("workers.tasks.execute_sequence_action", args=[str(a.id)])
    return len(actions)

