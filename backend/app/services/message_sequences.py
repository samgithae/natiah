import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sequence import MessageSequence


async def list_sequences(db: AsyncSession, campaign_id: uuid.UUID) -> list[MessageSequence]:
    res = await db.execute(
        select(MessageSequence)
        .where(MessageSequence.campaign_id == campaign_id)
        .order_by(MessageSequence.step_number.asc())
    )
    return list(res.scalars().all())


async def create_sequence(
    db: AsyncSession,
    *,
    campaign_id: uuid.UUID,
    step_number: int,
    delay_days: int,
    action_type: str,
    email_subject: str | None,
    message_template: str,
) -> MessageSequence:
    s = MessageSequence(
        campaign_id=campaign_id,
        step_number=step_number,
        delay_days=delay_days,
        action_type=action_type,
        email_subject=email_subject,
        message_template=message_template,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def get_sequence(db: AsyncSession, sequence_id: uuid.UUID) -> MessageSequence | None:
    res = await db.execute(select(MessageSequence).where(MessageSequence.id == sequence_id))
    return res.scalar_one_or_none()


async def update_sequence(
    db: AsyncSession,
    sequence_id: uuid.UUID,
    *,
    step_number: int | None,
    delay_days: int | None,
    action_type: str | None,
    email_subject: str | None,
    message_template: str | None,
) -> MessageSequence | None:
    s = await get_sequence(db, sequence_id)
    if not s:
        return None
    if step_number is not None:
        s.step_number = step_number
    if delay_days is not None:
        s.delay_days = delay_days
    if action_type is not None:
        s.action_type = action_type
    if email_subject is not None:
        s.email_subject = email_subject
    if message_template is not None:
        s.message_template = message_template
    await db.commit()
    await db.refresh(s)
    return s


async def delete_sequence(db: AsyncSession, sequence_id: uuid.UUID) -> bool:
    res = await db.execute(delete(MessageSequence).where(MessageSequence.id == sequence_id))
    await db.commit()
    return res.rowcount > 0
