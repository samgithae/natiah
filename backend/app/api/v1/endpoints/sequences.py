import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.message_sequence import (
    MessageSequenceCreate,
    MessageSequenceOut,
    MessageSequenceUpdate,
)
from app.services.campaigns import get_campaign
from app.services.message_sequences import (
    create_sequence,
    delete_sequence,
    get_sequence,
    list_sequences,
    update_sequence,
)


router = APIRouter()


@router.get("", response_model=list[MessageSequenceOut])
async def get_sequences(
    campaign_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    campaign = await get_campaign(db, user.id, campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    seqs = await list_sequences(db, campaign_id)
    return [
        MessageSequenceOut(
            id=s.id,
            campaign_id=s.campaign_id,
            step_number=s.step_number,
            delay_days=s.delay_days,
            action_type=s.action_type,
            email_subject=s.email_subject,
            message_template=s.message_template,
        )
        for s in seqs
    ]


@router.post("", response_model=MessageSequenceOut, status_code=status.HTTP_201_CREATED)
async def create_new_sequence(
    payload: MessageSequenceCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    campaign = await get_campaign(db, user.id, payload.campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    s = await create_sequence(
        db,
        campaign_id=payload.campaign_id,
        step_number=payload.step_number,
        delay_days=payload.delay_days,
        action_type=payload.action_type,
        email_subject=payload.email_subject,
        message_template=payload.message_template,
    )
    return MessageSequenceOut(
        id=s.id,
        campaign_id=s.campaign_id,
        step_number=s.step_number,
        delay_days=s.delay_days,
        action_type=s.action_type,
        email_subject=s.email_subject,
        message_template=s.message_template,
    )


@router.put("/{sequence_id}", response_model=MessageSequenceOut)
async def update_existing_sequence(
    sequence_id: uuid.UUID,
    payload: MessageSequenceUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    s = await get_sequence(db, sequence_id)
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sequence not found")
    campaign = await get_campaign(db, user.id, s.campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    s2 = await update_sequence(
        db,
        sequence_id,
        step_number=payload.step_number,
        delay_days=payload.delay_days,
        action_type=payload.action_type,
        email_subject=payload.email_subject,
        message_template=payload.message_template,
    )
    if not s2:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sequence not found")
    return MessageSequenceOut(
        id=s2.id,
        campaign_id=s2.campaign_id,
        step_number=s2.step_number,
        delay_days=s2.delay_days,
        action_type=s2.action_type,
        email_subject=s2.email_subject,
        message_template=s2.message_template,
    )


@router.delete("/{sequence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_sequence(
    sequence_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    s = await get_sequence(db, sequence_id)
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sequence not found")
    campaign = await get_campaign(db, user.id, s.campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    ok = await delete_sequence(db, sequence_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sequence not found")
    return None
