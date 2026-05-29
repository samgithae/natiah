from fastapi import APIRouter

from app.api.v1.endpoints import (
    accounts,
    analytics,
    auth,
    campaigns,
    email_enrichment,
    leads,
    mautic,
    settings,
    sequences,
)


api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
api_router.include_router(leads.router, prefix="/leads", tags=["leads"])
api_router.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])
api_router.include_router(sequences.router, prefix="/sequences", tags=["sequences"])
api_router.include_router(mautic.router, prefix="/integrations/mautic", tags=["mautic"])
api_router.include_router(
    email_enrichment.router,
    prefix="/integrations/email-enrichment",
    tags=["email-enrichment"],
)
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
