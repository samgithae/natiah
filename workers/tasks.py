import asyncio
import uuid
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.linkedin_account import LinkedInAccount
from app.models.message_event import MessageEvent
from app.models.sequence_action import SequenceAction
from app.models.sequence_enrollment import SequenceEnrollment
from app.services.automation_jobs import enqueue_automation_job
from app.services.leads import upsert_lead
from app.services.leads import clean_leads_bulk
from app.services.email_enrichment import enrich_lead_email, get_settings as get_email_settings
from app.services.mautic import bulk_sync
from app.services.sequence_engine import dispatch_due_actions, enroll_lead_in_campaign, schedule_sequence_actions


async def _with_db(fn):
    async with async_session_maker() as db:
        return await fn(db)


@shared_task(name="workers.tasks.scrape_sales_navigator")
def scrape_sales_navigator(linkedin_account_id: str, user_id_hex: str, search_url: str, limit: int = 50):
    try:
        account_id = uuid.UUID(linkedin_account_id)
    except ValueError:
        account_id = uuid.UUID(hex=linkedin_account_id)

    user_id = uuid.UUID(hex=user_id_hex)

    async def run(db: AsyncSession):
        job = await enqueue_automation_job(
            db,
            user_id=user_id,
            account_id=account_id,
            job_type="SCRAPE_SALES_NAVIGATOR",
            payload={"search_url": search_url, "limit": int(limit or 50)},
        )
        return {"status": "queued", "automation_job_id": str(job.id)}

    return asyncio.run(_with_db(run))


@shared_task(name="workers.tasks.find_emails")
def find_emails(user_id_hex: str, lead_ids: list[str]):
    user_id = uuid.UUID(hex=user_id_hex)
    lead_uuid_ids = [uuid.UUID(lid) for lid in lead_ids]

    async def run(db: AsyncSession):
        settings = await get_email_settings(db, user_id)
        res = await db.execute(select(Lead).where(Lead.id.in_(lead_uuid_ids)))
        leads = list(res.scalars().all())
        updated = 0
        failed = 0
        for l in leads:
            try:
                result = await enrich_lead_email(db, user_id=user_id, lead=l, settings=settings)
                if result and l.email:
                    updated += 1
            except Exception as e:
                failed += 1
                ev = MessageEvent(
                    user_id=user_id,
                    campaign_id=None,
                    lead_id=l.id,
                    channel="email_enrichment",
                    event_type="enrich_email",
                    status="failed",
                    payload=f"{type(e).__name__}: {e}",
                )
                db.add(ev)
                await db.commit()
        return {"updated": updated, "failed": failed}

    return asyncio.run(_with_db(run))


@shared_task(name="workers.tasks.clean_leads")
def clean_leads(user_id_hex: str, lead_ids: list[str]):
    user_id = uuid.UUID(hex=user_id_hex)
    lead_uuid_ids = [uuid.UUID(lid) for lid in lead_ids]

    async def run(db: AsyncSession):
        try:
            result = await clean_leads_bulk(db, user_id=user_id, lead_ids=lead_uuid_ids)
            ev = MessageEvent(
                user_id=user_id,
                campaign_id=None,
                lead_id=None,
                channel="lead_cleaning",
                event_type="bulk_clean",
                status="done",
                payload=str(result),
            )
            db.add(ev)
            await db.commit()
            return result
        except Exception as e:
            ev = MessageEvent(
                user_id=user_id,
                campaign_id=None,
                lead_id=None,
                channel="lead_cleaning",
                event_type="bulk_clean",
                status="failed",
                payload=f"{type(e).__name__}: {e}",
            )
            db.add(ev)
            await db.commit()
            raise

    return asyncio.run(_with_db(run))


@shared_task(name="workers.tasks.sync_mautic")
def sync_mautic(user_id_hex: str, lead_ids: list[str], tags: list[str] | None = None, segment_ids: list[int] | None = None):
    user_id = uuid.UUID(hex=user_id_hex)
    lead_uuid_ids = [uuid.UUID(lid) for lid in lead_ids]

    async def run(db: AsyncSession):
        result = await bulk_sync(
            db,
            user_id=user_id,
            lead_ids=lead_uuid_ids,
            tags=tags or [],
            segment_ids=segment_ids or [],
        )
        for r in result.get("results", []):
            status = r.get("status")
            lead_id_str = r.get("lead_id")
            lead_uuid = uuid.UUID(lead_id_str) if lead_id_str else None
            ev = MessageEvent(
                user_id=user_id,
                campaign_id=None,
                lead_id=lead_uuid,
                channel="mautic",
                event_type="sync_contact",
                status="done" if status == "ok" else "failed",
                payload=str(r),
            )
            db.add(ev)
        await db.commit()
        return {"provider": "mautic", "ok": result["ok"], "failed": result["failed"]}

    return asyncio.run(_with_db(run))


@shared_task(name="workers.tasks.run_campaign")
def run_campaign(campaign_id: str, user_id: str):
    campaign_uuid = uuid.UUID(campaign_id)
    user_uuid = uuid.UUID(user_id)

    async def run(db: AsyncSession):
        account_ids_res = await db.execute(
            select(LinkedInAccount.id).where(LinkedInAccount.user_id == user_uuid)
        )
        account_ids = [r[0] for r in account_ids_res.all()]
        if not account_ids:
            return {"actions_scheduled": 0}
        res = await db.execute(select(Lead).where(Lead.account_id.in_(account_ids)).limit(25))
        leads = list(res.scalars().all())
        created = 0
        for l in leads:
            enr = await enroll_lead_in_campaign(db, campaign_id=campaign_uuid, lead_id=l.id)
            created += await schedule_sequence_actions(db, enrollment=enr)
        return {"actions_scheduled": created}

    return asyncio.run(_with_db(run))


@shared_task(name="workers.tasks.scheduled_tick")
def scheduled_tick():
    async def run(db: AsyncSession):
        total_scheduled = 0
        res = await db.execute(select(Campaign).where(Campaign.status == "running"))
        campaigns = list(res.scalars().all())
        for c in campaigns:
            account_ids_res = await db.execute(
                select(LinkedInAccount.id).where(LinkedInAccount.user_id == c.user_id)
            )
            account_ids = [r[0] for r in account_ids_res.all()]
            if not account_ids:
                continue

            enrolled_subq = (
                select(SequenceEnrollment.lead_id).where(SequenceEnrollment.campaign_id == c.id).subquery()
            )
            leads_res = await db.execute(
                select(Lead)
                .where(Lead.account_id.in_(account_ids), ~Lead.id.in_(select(enrolled_subq.c.lead_id)))
                .order_by(Lead.created_at.asc())
                .limit(25)
            )
            leads = list(leads_res.scalars().all())
            for l in leads:
                enr = await enroll_lead_in_campaign(db, campaign_id=c.id, lead_id=l.id)
                total_scheduled += await schedule_sequence_actions(db, enrollment=enr)

        dispatched = await dispatch_due_actions(db, limit=200)
        return {"dispatched": dispatched, "actions_scheduled": total_scheduled}

    return asyncio.run(_with_db(run))


@shared_task(
    name="workers.tasks.execute_sequence_action",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def execute_sequence_action(sequence_action_id: str):
    action_uuid = uuid.UUID(sequence_action_id)

    async def run(db: AsyncSession):
        res = await db.execute(select(SequenceAction).where(SequenceAction.id == action_uuid))
        action = res.scalar_one_or_none()
        if not action:
            return {"status": "missing"}
        if action.status in {"done", "canceled"}:
            return {"status": action.status}

        action.attempts = int(action.attempts or 0) + 1
        await db.commit()

        try:
            payload = action.payload or {}
            template = payload.get("template") or ""
            email_subject = payload.get("email_subject")

            if action.action_type == "connect":
                channel = "linkedin"
                event_type = "connect_request"
            elif action.action_type == "linkedin_message":
                channel = "linkedin"
                event_type = "linkedin_message"
            elif action.action_type == "email":
                channel = "email"
                event_type = "email_send"
            else:
                channel = "unknown"
                event_type = action.action_type

            camp_res = await db.execute(select(Campaign).where(Campaign.id == action.campaign_id))
            campaign = camp_res.scalar_one_or_none()
            if not campaign:
                raise RuntimeError("Campaign not found")

            lead_res = await db.execute(select(Lead).where(Lead.id == action.lead_id))
            lead = lead_res.scalar_one_or_none()
            if not lead:
                raise RuntimeError("Lead not found")

            job_id = None
            if action.action_type == "connect":
                job = await enqueue_automation_job(
                    db,
                    user_id=campaign.user_id,
                    account_id=lead.account_id,
                    job_type="CONNECT",
                    payload={"profile_url": lead.linkedin_url, "note": template or None},
                    run_at=datetime.now(timezone.utc),
                )
                job_id = str(job.id)
            elif action.action_type == "linkedin_message":
                thread_url = None
                if isinstance(lead.raw_data, dict):
                    thread_url = lead.raw_data.get("thread_url")
                job = await enqueue_automation_job(
                    db,
                    user_id=campaign.user_id,
                    account_id=lead.account_id,
                    job_type="SEND_FOLLOW_UP",
                    payload={"thread_url": thread_url or lead.linkedin_url, "message": template},
                    run_at=datetime.now(timezone.utc),
                )
                job_id = str(job.id)

            ev = MessageEvent(
                user_id=campaign.user_id,
                campaign_id=action.campaign_id,
                lead_id=action.lead_id,
                channel=channel,
                event_type=event_type,
                status="queued",
                payload=str({"template": template, "email_subject": email_subject, "automation_job_id": job_id}),
            )
            db.add(ev)

            action.status = "done"
            action.executed_at = datetime.now(timezone.utc)
            action.last_error = None
            await db.commit()
            return {"status": "done", "event_type": event_type}
        except Exception as e:
            action.status = "failed"
            action.last_error = f"{type(e).__name__}: {e}"
            await db.commit()
            raise

    return asyncio.run(_with_db(run))
