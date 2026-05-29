from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.linkedin_account import LinkedInAccount
from app.models.message_event import MessageEvent
from app.schemas.analytics import AnalyticsOverview, CampaignPerformanceRow, DailyActivityPoint, DashboardStats


router = APIRouter()


@router.get("/dashboard", response_model=DashboardStats)
async def dashboard_stats(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    accounts_res = await db.execute(
        select(func.count()).select_from(LinkedInAccount).where(LinkedInAccount.user_id == user.id)
    )
    lead_accounts_subq = select(LinkedInAccount.id).where(LinkedInAccount.user_id == user.id)
    leads_res = await db.execute(
        select(func.count()).select_from(Lead).where(Lead.account_id.in_(lead_accounts_subq))
    )
    campaigns_res = await db.execute(
        select(func.count()).select_from(Campaign).where(Campaign.user_id == user.id)
    )
    return DashboardStats(
        accounts=int(accounts_res.scalar_one()),
        leads=int(leads_res.scalar_one()),
        campaigns=int(campaigns_res.scalar_one()),
    )


@router.get("/overview", response_model=AnalyticsOverview)
async def analytics_overview(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    days = max(1, min(int(days), 365))
    start = datetime.now(timezone.utc) - timedelta(days=days)

    res = await db.execute(
        select(MessageEvent.event_type, func.count())
        .where(MessageEvent.user_id == user.id, MessageEvent.created_at >= start)
        .group_by(MessageEvent.event_type)
    )
    counts = {str(r[0]): int(r[1]) for r in res.all()}

    connections_sent = int(counts.get("connect_request", 0))
    connections_accepted = int(counts.get("connection_accepted", 0))
    replies = int(counts.get("linkedin_reply", 0) + counts.get("email_reply", 0) + counts.get("reply", 0))
    emails_sent = int(counts.get("email_send", 0))
    email_opens = int(counts.get("email_open", 0))
    conversions = int(counts.get("conversion", 0) + counts.get("converted", 0))

    acceptance_rate = (connections_accepted / connections_sent) if connections_sent else 0.0
    reply_rate = (replies / connections_sent) if connections_sent else 0.0
    email_open_rate = (email_opens / emails_sent) if emails_sent else 0.0
    conversion_rate = (conversions / connections_sent) if connections_sent else 0.0

    return AnalyticsOverview(
        connections_sent=connections_sent,
        connections_accepted=connections_accepted,
        connection_acceptance_rate=float(acceptance_rate),
        replies=replies,
        reply_rate=float(reply_rate),
        emails_sent=emails_sent,
        email_opens=email_opens,
        email_open_rate=float(email_open_rate),
        conversions=conversions,
        conversion_rate=float(conversion_rate),
    )


@router.get("/daily-activity", response_model=list[DailyActivityPoint])
async def daily_activity(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    days = max(1, min(int(days), 365))
    start = datetime.now(timezone.utc) - timedelta(days=days)

    day_col = func.date_trunc("day", MessageEvent.created_at)
    res = await db.execute(
        select(day_col.label("d"), MessageEvent.event_type, func.count())
        .where(MessageEvent.user_id == user.id, MessageEvent.created_at >= start)
        .group_by("d", MessageEvent.event_type)
        .order_by("d")
    )
    rows = res.all()

    by_day: dict[str, dict[str, int]] = {}
    for d, event_type, cnt in rows:
        key = d.date().isoformat() if hasattr(d, "date") else str(d)
        bucket = by_day.setdefault(key, {"connections_sent": 0, "replies": 0, "emails_sent": 0})
        et = str(event_type)
        if et == "connect_request":
            bucket["connections_sent"] += int(cnt)
        elif et in {"linkedin_reply", "email_reply", "reply"}:
            bucket["replies"] += int(cnt)
        elif et == "email_send":
            bucket["emails_sent"] += int(cnt)

    out: list[DailyActivityPoint] = []
    for day, data in by_day.items():
        out.append(
            DailyActivityPoint(
                date=day,
                connections_sent=int(data["connections_sent"]),
                replies=int(data["replies"]),
                emails_sent=int(data["emails_sent"]),
            )
        )
    return out


@router.get("/campaign-performance", response_model=list[CampaignPerformanceRow])
async def campaign_performance(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    days = max(1, min(int(days), 365))
    start = datetime.now(timezone.utc) - timedelta(days=days)

    campaigns_res = await db.execute(select(Campaign).where(Campaign.user_id == user.id))
    campaigns = list(campaigns_res.scalars().all())
    if not campaigns:
        return []

    res = await db.execute(
        select(MessageEvent.campaign_id, MessageEvent.event_type, func.count())
        .where(
            MessageEvent.user_id == user.id,
            MessageEvent.created_at >= start,
            MessageEvent.campaign_id.is_not(None),
        )
        .group_by(MessageEvent.campaign_id, MessageEvent.event_type)
    )
    counts: dict[str, dict[str, int]] = {}
    for campaign_id, event_type, cnt in res.all():
        cid = str(campaign_id)
        bucket = counts.setdefault(cid, {})
        bucket[str(event_type)] = int(cnt)

    out: list[CampaignPerformanceRow] = []
    for c in campaigns:
        bucket = counts.get(str(c.id), {})
        out.append(
            CampaignPerformanceRow(
                campaign_id=c.id,
                campaign_name=c.name,
                connections_sent=int(bucket.get("connect_request", 0)),
                replies=int(bucket.get("linkedin_reply", 0) + bucket.get("email_reply", 0) + bucket.get("reply", 0)),
                emails_sent=int(bucket.get("email_send", 0)),
            )
        )
    return out
