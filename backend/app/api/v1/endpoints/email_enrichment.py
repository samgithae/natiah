from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.email_enrichment import (
    EmailEnrichmentRequest,
    EmailEnrichmentSettingsIn,
    EmailEnrichmentSettingsOut,
)
from app.services.campaigns import celery_client
from app.services.email_enrichment import get_settings, upsert_settings


router = APIRouter()


@router.get("/settings", response_model=EmailEnrichmentSettingsOut)
async def get_email_settings(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    s = await get_settings(db, user.id)
    if not s:
        return EmailEnrichmentSettingsOut(
            hunter_api_key_set=False,
            apollo_api_key_set=False,
            prospeo_api_key_set=False,
        )
    return EmailEnrichmentSettingsOut(
        hunter_api_key_set=bool(s.hunter_api_key),
        apollo_api_key_set=bool(s.apollo_api_key),
        prospeo_api_key_set=bool(s.prospeo_api_key),
    )


@router.put("/settings", response_model=EmailEnrichmentSettingsOut)
async def put_email_settings(
    payload: EmailEnrichmentSettingsIn,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    s = await upsert_settings(
        db,
        user_id=user.id,
        hunter_api_key=payload.hunter_api_key,
        apollo_api_key=payload.apollo_api_key,
        prospeo_api_key=payload.prospeo_api_key,
    )
    return EmailEnrichmentSettingsOut(
        hunter_api_key_set=bool(s.hunter_api_key),
        apollo_api_key_set=bool(s.apollo_api_key),
        prospeo_api_key_set=bool(s.prospeo_api_key),
    )


@router.post("/enrich")
async def enqueue_enrichment(payload: EmailEnrichmentRequest, user=Depends(get_current_user)):
    if not payload.lead_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="lead_ids required")
    task = celery_client.send_task("workers.tasks.find_emails", args=[user.id.hex, payload.lead_ids])
    return {"task_id": task.id}

