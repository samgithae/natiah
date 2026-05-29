import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.lead import LeadCreate, LeadOut
from app.services.campaigns import celery_client
from app.services.leads import export_leads_csv, list_leads, upsert_lead


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
    user=Depends(get_current_user),
):
    task = celery_client.send_task(
        "workers.tasks.scrape_sales_navigator",
        args=[linkedin_account_id, user.id.hex, search_url],
    )
    return {"task_id": task.id}


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
