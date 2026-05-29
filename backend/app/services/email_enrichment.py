import re
import uuid
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_enrichment import EmailEnrichmentResult, EmailEnrichmentSettings
from app.models.lead import Lead


def _clean_name(s: str | None) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def _clean_domain(d: str | None) -> str:
    d = (d or "").strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = d.split("/")[0]
    d = d.replace("www.", "")
    d = re.sub(r"[^a-z0-9.-]+", "", d)
    return d


def generate_email_patterns(first_name: str | None, last_name: str | None, domain: str) -> list[str]:
    first = _clean_name(first_name)
    last = _clean_name(last_name)
    domain = _clean_domain(domain)
    if not domain:
        return []
    candidates: list[str] = []
    if first:
        candidates.append(f"{first}@{domain}")
    if first and last:
        candidates.append(f"{first}.{last}@{domain}")
        candidates.append(f"{first[0]}{last}@{domain}")
    dedup: list[str] = []
    seen = set()
    for c in candidates:
        if c in seen:
            continue
        seen.add(c)
        dedup.append(c)
    return dedup


@dataclass
class VerifiedEmail:
    email: str
    status: str
    confidence: int
    provider: str
    details: dict[str, Any]


async def get_settings(db: AsyncSession, user_id: uuid.UUID) -> EmailEnrichmentSettings | None:
    res = await db.execute(select(EmailEnrichmentSettings).where(EmailEnrichmentSettings.user_id == user_id))
    return res.scalar_one_or_none()


async def upsert_settings(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    hunter_api_key: str | None,
    apollo_api_key: str | None,
    prospeo_api_key: str | None,
) -> EmailEnrichmentSettings:
    s = await get_settings(db, user_id)
    if s:
        if hunter_api_key is not None:
            s.hunter_api_key = hunter_api_key
        if apollo_api_key is not None:
            s.apollo_api_key = apollo_api_key
        if prospeo_api_key is not None:
            s.prospeo_api_key = prospeo_api_key
        await db.commit()
        await db.refresh(s)
        return s
    s = EmailEnrichmentSettings(
        user_id=user_id,
        hunter_api_key=hunter_api_key,
        apollo_api_key=apollo_api_key,
        prospeo_api_key=prospeo_api_key,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def _hunter_email_verifier(api_key: str, email: str) -> VerifiedEmail | None:
    url = "https://api.hunter.io/v2/email-verifier"
    async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=15.0)) as client:
        resp = await client.get(url, params={"email": email, "api_key": api_key})
        if resp.status_code >= 400:
            return None
        data = resp.json().get("data") or {}
        status = str(data.get("status") or "unknown")
        score = int(data.get("score") or 0)
        confidence = min(100, max(0, score))
        return VerifiedEmail(
            email=email,
            status=status,
            confidence=confidence,
            provider="hunter",
            details=data,
        )


async def _hunter_domain_search(api_key: str, company: str) -> str | None:
    url = "https://api.hunter.io/v2/domain-search"
    async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=15.0)) as client:
        resp = await client.get(url, params={"company": company, "api_key": api_key, "limit": 1})
        if resp.status_code >= 400:
            return None
        data = resp.json().get("data") or {}
        domain = data.get("domain")
        return _clean_domain(domain) or None


async def _apollo_company_domain(api_key: str, company: str) -> str | None:
    url = "https://api.apollo.io/v1/organizations/enrich"
    async with httpx.AsyncClient(timeout=httpx.Timeout(25.0, connect=15.0)) as client:
        resp = await client.post(url, json={"api_key": api_key, "organization_name": company})
        if resp.status_code >= 400:
            return None
        data = resp.json()
        org = data.get("organization") or {}
        domain = org.get("website_url") or org.get("primary_domain")
        return _clean_domain(domain) or None


async def _prospeo_verify(api_key: str, email: str) -> VerifiedEmail | None:
    url = "https://api.prospeo.io/v1/email/verify"
    async with httpx.AsyncClient(timeout=httpx.Timeout(25.0, connect=15.0)) as client:
        resp = await client.post(url, json={"api_key": api_key, "email": email})
        if resp.status_code >= 400:
            return None
        data = resp.json()
        status = str(data.get("status") or data.get("result") or "unknown")
        confidence = int(data.get("confidence") or 0)
        if confidence <= 0:
            confidence = 60 if status in {"valid", "deliverable"} else 20
        return VerifiedEmail(
            email=email,
            status=status,
            confidence=min(100, max(0, confidence)),
            provider="prospeo",
            details=data,
        )


async def find_company_domain(db: AsyncSession, *, settings: EmailEnrichmentSettings | None, lead: Lead) -> str | None:
    if isinstance(lead.raw_data, dict):
        d = _clean_domain(lead.raw_data.get("domain"))
        if d:
            return d
    if lead.company and "." in lead.company and " " not in lead.company:
        return _clean_domain(lead.company)
    company = lead.company or ""
    if not company:
        return None
    if settings and settings.hunter_api_key:
        d = await _hunter_domain_search(settings.hunter_api_key, company)
        if d:
            return d
    if settings and settings.apollo_api_key:
        d = await _apollo_company_domain(settings.apollo_api_key, company)
        if d:
            return d
    return None


def _score_candidate(email: str, verified: VerifiedEmail | None) -> int:
    base = 10
    if verified:
        base = verified.confidence
        st = (verified.status or "").lower()
        if st in {"valid", "deliverable"}:
            base = max(base, 80)
        if st in {"invalid", "undeliverable"}:
            base = min(base, 10)
    if email.endswith("@gmail.com") or email.endswith("@yahoo.com") or email.endswith("@hotmail.com"):
        base = min(base, 40)
    return min(100, max(0, base))


async def enrich_lead_email(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    lead: Lead,
    settings: EmailEnrichmentSettings | None,
) -> VerifiedEmail | None:
    domain = await find_company_domain(db, settings=settings, lead=lead)
    if not domain:
        return None

    candidates = generate_email_patterns(lead.first_name, lead.last_name, domain)
    if not candidates:
        return None

    verifications: list[VerifiedEmail] = []
    for email in candidates:
        verified: VerifiedEmail | None = None
        if settings and settings.hunter_api_key:
            verified = await _hunter_email_verifier(settings.hunter_api_key, email)
        if not verified and settings and settings.prospeo_api_key:
            verified = await _prospeo_verify(settings.prospeo_api_key, email)
        if not verified:
            verified = VerifiedEmail(
                email=email,
                status="unknown",
                confidence=35,
                provider="pattern",
                details={"domain": domain, "pattern": "generated"},
            )
        verified = VerifiedEmail(
            email=email,
            status=verified.status,
            confidence=_score_candidate(email, verified),
            provider=verified.provider,
            details=verified.details,
        )
        verifications.append(verified)

    best = sorted(verifications, key=lambda v: v.confidence, reverse=True)[0]
    db.add(
        EmailEnrichmentResult(
            user_id=user_id,
            lead_id=lead.id,
            provider=best.provider,
            email=best.email,
            status=best.status,
            confidence=best.confidence,
            details=best.details,
        )
    )
    if best.status.lower() in {"valid", "deliverable"} or best.confidence >= 75:
        lead.email = best.email
        if isinstance(lead.raw_data, dict):
            lead.raw_data = {**lead.raw_data, "domain": domain, "email_confidence": best.confidence}
    await db.commit()
    return best

