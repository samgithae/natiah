import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.automation_job import AutomationJob
from app.schemas.lead import LeadCreate, LeadOut
from app.services.account_service import get_linkedin_account
from app.services.automation_jobs import enqueue_automation_job
from app.services.campaigns import celery_client, create_campaign, start_campaign
from app.services.leads import export_leads_csv, list_leads, upsert_lead
from app.services.message_sequences import create_sequence
from app.services.playwright_manager import close_persistent_context, launch_persistent_context
from app.services.linkedin_session_service import open_and_verify


router = APIRouter()


@router.get("", response_model=list[LeadOut])
async def get_leads(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    leads = await list_leads(db, account_id, limit=limit, offset=offset)
    return [
        LeadOut(
            id=l.id,
            account_id=l.account_id,
            first_name=l.first_name,
            last_name=l.last_name,
            company=l.company,
            job_title=l.job_title,
            linkedin_url=l.linkedin_url,
            email=l.email,
            status=l.status,
        )
        for l in leads
    ]


@router.post("", response_model=LeadOut)
async def upsert_one_lead(
    payload: LeadCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    lead = await upsert_lead(db, payload.model_dump())
    return LeadOut(
        id=lead.id,
        account_id=lead.account_id,
        first_name=lead.first_name,
        last_name=lead.last_name,
        company=lead.company,
        job_title=lead.job_title,
        linkedin_url=lead.linkedin_url,
        email=lead.email,
        status=lead.status,
    )


@router.get("/export.csv")
async def export_csv(account_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    content = await export_leads_csv(db, account_id)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="leads.csv"'},
    )


@router.post("/scrape/sales-navigator")
async def scrape_sales_navigator(
    search_url: str,
    linkedin_account_id: str,
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        account_uuid = uuid.UUID(str(linkedin_account_id))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid linkedin_account_id")

    a = await get_linkedin_account(db, user_id=user.id, account_id=account_uuid)
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    task = celery_client.send_task(
        "workers.tasks.scrape_sales_navigator",
        args=[str(a.id), user.id.hex, search_url, int(limit)],
    )
    return {"task_id": task.id}


class ExtractSearchIn(BaseModel):
    account_id: uuid.UUID
    search_url: str = Field(min_length=1, max_length=2000)
    connect_note: str | None = Field(default=None, max_length=300)
    message: str | None = Field(default=None, max_length=3000)
    followups: list[str] = Field(default_factory=list)
    lead_limit: int = Field(default=50, ge=1, le=500)
    campaign_name: str | None = Field(default=None, min_length=1, max_length=200)


class ExtractSearchOut(BaseModel):
    campaign_id: uuid.UUID
    automation_job_id: uuid.UUID
    status: str


@router.post("/extract-search", response_model=ExtractSearchOut, status_code=status.HTTP_202_ACCEPTED)
async def extract_search(
    payload: ExtractSearchIn,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    a = await get_linkedin_account(db, user_id=user.id, account_id=payload.account_id)
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if not a.session_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing session profile path")

    ctx = await launch_persistent_context(
        user_data_dir=a.session_path,
        headless=True,
        slow_mo_ms=0,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-infobars",
            "--disable-notifications",
        ],
    )
    try:
        chk = await open_and_verify(ctx.context, ctx.page)
        if chk.status != "connected":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="LinkedIn session not connected. Go to Accounts → Connect for Automation and paste your li_at cookie, then verify and retry.",
            )
    finally:
        await close_persistent_context(ctx.context)

    campaign = await create_campaign(
        db,
        user.id,
        name=payload.campaign_name or "Search Extract",
        daily_limit=50,
    )

    step_number = 1
    await create_sequence(
        db,
        campaign_id=campaign.id,
        step_number=step_number,
        delay_days=0,
        action_type="connect",
        email_subject=None,
        message_template=payload.connect_note or "",
    )
    step_number += 1

    if payload.message and payload.message.strip():
        await create_sequence(
            db,
            campaign_id=campaign.id,
            step_number=step_number,
            delay_days=2,
            action_type="linkedin_message",
            email_subject=None,
            message_template=payload.message.strip(),
        )
        step_number += 1

    delay = 4
    for f in payload.followups:
        txt = (f or "").strip()
        if not txt:
            continue
        await create_sequence(
            db,
            campaign_id=campaign.id,
            step_number=step_number,
            delay_days=delay,
            action_type="linkedin_message",
            email_subject=None,
            message_template=txt,
        )
        step_number += 1
        delay += 2

    job = await enqueue_automation_job(
        db,
        user_id=user.id,
        account_id=a.id,
        job_type="SCRAPE_SALES_NAVIGATOR",
        payload={"search_url": payload.search_url, "limit": int(payload.lead_limit)},
    )

    await start_campaign(db, user.id, campaign.id)

    return ExtractSearchOut(campaign_id=campaign.id, automation_job_id=job.id, status="started")


class AutomationJobStatusOut(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    job_type: str
    status: str
    attempts: int
    locked_by: str | None = None
    last_error: str | None = None


@router.get("/automation-jobs/{job_id}", response_model=AutomationJobStatusOut)
async def get_automation_job_status(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    res = await db.execute(select(AutomationJob).where(AutomationJob.id == job_id, AutomationJob.user_id == user.id))
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return AutomationJobStatusOut(
        id=job.id,
        account_id=job.account_id,
        job_type=job.job_type,
        status=job.status,
        attempts=int(job.attempts or 0),
        locked_by=job.locked_by,
        last_error=job.last_error,
    )


@router.post("/email-finder")
async def run_email_finder(lead_ids: list[str], user=Depends(get_current_user)):
    task = celery_client.send_task("workers.tasks.find_emails", args=[user.id.hex, lead_ids])
    return {"task_id": task.id}


@router.post("/mautic/sync")
async def sync_to_mautic(lead_ids: list[str], user=Depends(get_current_user)):
    task = celery_client.send_task("workers.tasks.sync_mautic", args=[user.id.hex, lead_ids])
    return {"task_id": task.id}


@router.post("/clean")
async def clean_leads(lead_ids: list[str], user=Depends(get_current_user)):
    task = celery_client.send_task("workers.tasks.clean_leads", args=[user.id.hex, lead_ids])
    return {"task_id": task.id}
