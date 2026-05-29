import uuid

from pydantic import BaseModel


class DashboardStats(BaseModel):
    accounts: int
    leads: int
    campaigns: int


class AnalyticsOverview(BaseModel):
    connections_sent: int
    connections_accepted: int
    connection_acceptance_rate: float

    replies: int
    reply_rate: float

    emails_sent: int
    email_opens: int
    email_open_rate: float

    conversions: int
    conversion_rate: float


class DailyActivityPoint(BaseModel):
    date: str
    connections_sent: int
    replies: int
    emails_sent: int


class CampaignPerformanceRow(BaseModel):
    campaign_id: uuid.UUID
    campaign_name: str
    connections_sent: int
    replies: int
    emails_sent: int
