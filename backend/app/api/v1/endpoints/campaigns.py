import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.campaign import CampaignCreate, CampaignOut, CampaignUpdate
from app.services.campaigns import (
    create_campaign,
    delete_campaign,
    get_campaign,
    list_campaigns,
    start_campaign,
    stop_campaign,
    update_campaign,
)


router = APIRouter()


@router.get("", response_model=list[CampaignOut])
async def get_campaigns(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    campaigns = await list_campaigns(db, user.id)
    return [
        CampaignOut(
            id=c.id,
            name=c.name,
            status=c.status,
            daily_limit=c.daily_limit,
        )
        for c in campaigns
    ]


@router.post("", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
async def create_new_campaign(
    payload: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    c = await create_campaign(
        db, user.id, name=payload.name, daily_limit=payload.daily_limit
    )
    return CampaignOut(
        id=c.id, name=c.name, status=c.status, daily_limit=c.daily_limit
    )


@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_one_campaign(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    c = await get_campaign(db, user.id, campaign_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return CampaignOut(
        id=c.id, name=c.name, status=c.status, daily_limit=c.daily_limit
    )


@router.put("/{campaign_id}", response_model=CampaignOut)
async def update_one_campaign(
    campaign_id: uuid.UUID,
    payload: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    c = await update_campaign(
        db,
        user.id,
        campaign_id,
        name=payload.name,
        status=payload.status,
        daily_limit=payload.daily_limit,
    )
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return CampaignOut(
        id=c.id, name=c.name, status=c.status, daily_limit=c.daily_limit
    )


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_one_campaign(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    ok = await delete_campaign(db, user.id, campaign_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return None


@router.post("/{campaign_id}/start")
async def start_one_campaign(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    ok = await start_campaign(db, user.id, campaign_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return {"status": "started"}


@router.post("/{campaign_id}/stop")
async def stop_one_campaign(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    ok = await stop_campaign(db, user.id, campaign_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return {"status": "stopped"}
