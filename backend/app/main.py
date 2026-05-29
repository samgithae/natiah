import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api.v1.api import api_router
from app.core.config import settings
from app.db.base import Base
from app.core.security import hash_password
from app.db.session import async_session_maker, engine
from app.models.app_settings import AppSettings
from app.models.automation_job import AutomationJob
from app.models.automation_state import AutomationAccountDayStats, AutomationAccountState
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.linkedin_account import LinkedInAccount
from app.models.message_event import MessageEvent
from app.models.email_enrichment import EmailEnrichmentResult, EmailEnrichmentSettings
from app.models.mautic_settings import MauticSettings
from app.models.sequence_action import SequenceAction
from app.models.sequence_enrollment import SequenceEnrollment
from app.models.sequence import MessageSequence
from app.models.user import User


app = FastAPI(title=settings.project_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health():
    return {"ok": True}


@app.on_event("startup")
async def startup():
    if settings.db_auto_create:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    admin_email = (os.environ.get("NATIAH_ADMIN_EMAIL") or "").strip().lower()
    admin_password = os.environ.get("NATIAH_ADMIN_PASSWORD") or ""
    if admin_email and admin_password:
        try:
            if len(admin_password.encode("utf-8")) > 72:
                logging.getLogger("natiah").warning("Admin password too long for bcrypt; skipping auto-seed")
                return
            async with async_session_maker() as db:
                res = await db.execute(select(User).where(User.email == admin_email))
                existing = res.scalar_one_or_none()
                if not existing:
                    db.add(User(email=admin_email, hashed_password=hash_password(admin_password)))
                    await db.commit()
        except Exception:
            logging.getLogger("natiah").exception("Admin auto-seed failed")
