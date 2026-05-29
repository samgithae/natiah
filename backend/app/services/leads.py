import csv
import io
import re
import uuid
from urllib.parse import urlparse, urlunparse

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.linkedin_account import LinkedInAccount
from app.models.lead import Lead


async def list_leads(
    db: AsyncSession, account_id: uuid.UUID, limit: int = 100, offset: int = 0
) -> list[Lead]:
    res = await db.execute(
        select(Lead)
        .where(Lead.account_id == account_id)
        .order_by(Lead.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(res.scalars().all())


async def upsert_lead(db: AsyncSession, payload: dict) -> Lead:
    stmt = (
        insert(Lead)
        .values(**payload)
        .on_conflict_do_update(
            constraint="uq_leads_account_linkedin",
            set_={
                "email": payload.get("email"),
                "first_name": payload.get("first_name"),
                "last_name": payload.get("last_name"),
                "company": payload.get("company"),
                "job_title": payload.get("job_title"),
                "status": payload.get("status"),
                "raw_data": payload.get("raw_data"),
            },
        )
        .returning(Lead.id)
    )
    res = await db.execute(stmt)
    lead_id = res.scalar_one()
    await db.commit()
    lead_res = await db.execute(select(Lead).where(Lead.id == lead_id))
    return lead_res.scalar_one()


async def export_leads_csv(db: AsyncSession, account_id: uuid.UUID) -> bytes:
    res = await db.execute(
        select(Lead).where(Lead.account_id == account_id).order_by(Lead.created_at.desc())
    )
    leads = list(res.scalars().all())

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "account_id",
            "linkedin_url",
            "email",
            "first_name",
            "last_name",
            "company",
            "job_title",
            "location",
            "status",
        ]
    )
    for l in leads:
        location = ""
        if isinstance(l.raw_data, dict):
            location = str(l.raw_data.get("location") or "")
        writer.writerow(
            [
                str(l.account_id),
                l.linkedin_url,
                l.email or "",
                l.first_name or "",
                l.last_name or "",
                l.company or "",
                l.job_title or "",
                location,
                l.status or "",
            ]
        )
    return output.getvalue().encode("utf-8")


_EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.IGNORECASE)


def _collapse_ws(s: str) -> str:
    return " ".join((s or "").strip().split())


def normalize_company_name(company: str | None) -> str | None:
    if company is None:
        return None
    c = _collapse_ws(company)
    c = c.strip(" \t\r\n\"'")
    c = c.rstrip(".,;")
    return c or None


def canonicalize_linkedin_url(url: str | None) -> tuple[str | None, bool]:
    raw = (url or "").strip()
    if not raw:
        return None, False
    if "://" not in raw:
        raw = f"https://{raw}"
    try:
        p = urlparse(raw)
    except Exception:
        return None, False

    host = (p.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if not host.endswith("linkedin.com"):
        return None, False

    path = (p.path or "").strip()
    if not path.startswith("/"):
        path = f"/{path}"
    path = path.rstrip("/")

    is_valid_path = any(
        path.startswith(prefix)
        for prefix in (
            "/in/",
            "/sales/people/",
            "/sales/lead/",
            "/company/",
        )
    )
    canonical = urlunparse(("https", f"www.{host}" if not host.startswith("www.") else host, path, "", "", ""))
    return canonical, bool(is_valid_path)


def validate_email(email: str | None) -> bool:
    e = (email or "").strip()
    if not e:
        return True
    if len(e) > 320:
        return False
    return bool(_EMAIL_RE.match(e))


def _lead_completeness_score(l: Lead) -> int:
    score = 0
    if l.email:
        score += 20
    if l.company:
        score += 10
    if l.job_title:
        score += 10
    if l.first_name:
        score += 5
    if l.last_name:
        score += 5
    return score


async def clean_leads_bulk(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    lead_ids: list[uuid.UUID],
) -> dict:
    if not lead_ids:
        return {"processed": 0}

    res = await db.execute(
        select(Lead)
        .join(LinkedInAccount, Lead.account_id == LinkedInAccount.id)
        .where(LinkedInAccount.user_id == user_id, Lead.id.in_(lead_ids))
    )
    leads = list(res.scalars().all())
    if not leads:
        return {"processed": 0}

    processed = 0
    invalid_url = 0
    emails_cleared = 0
    company_normalized = 0
    incomplete_profiles = 0
    duplicates = 0

    canonical_map: dict[str, list[Lead]] = {}
    for l in leads:
        processed += 1
        raw = l.raw_data if isinstance(l.raw_data, dict) else {}

        canonical_url, is_valid = canonicalize_linkedin_url(l.linkedin_url)
        raw = {**raw, "linkedin_url_canonical": canonical_url, "linkedin_url_valid": is_valid}
        if not is_valid:
            invalid_url += 1
            if l.status != "invalid":
                l.status = "invalid"

        normalized_company = normalize_company_name(l.company)
        if normalized_company != l.company:
            company_normalized += 1
            raw = {**raw, "company_original": l.company, "company_normalized": normalized_company}
            l.company = normalized_company

        if l.email and not validate_email(l.email):
            emails_cleared += 1
            raw = {**raw, "email_invalid": True, "email_original": l.email}
            l.email = None

        missing_fields: list[str] = []
        if not (l.first_name or "").strip():
            missing_fields.append("first_name")
        if not (l.last_name or "").strip():
            missing_fields.append("last_name")
        if not (l.company or "").strip():
            missing_fields.append("company")
        if not (l.job_title or "").strip():
            missing_fields.append("job_title")
        if missing_fields:
            incomplete_profiles += 1
            raw = {**raw, "incomplete_profile": True, "missing_fields": missing_fields}
        else:
            raw = {**raw, "incomplete_profile": False}

        l.raw_data = raw

        key = canonical_url or ""
        if key:
            canonical_map.setdefault(key, []).append(l)

    for url, items in canonical_map.items():
        if len(items) <= 1:
            continue
        items_sorted = sorted(items, key=_lead_completeness_score, reverse=True)
        winner = items_sorted[0]
        for dup in items_sorted[1:]:
            if dup.status != "duplicate":
                dup.status = "duplicate"
            raw = dup.raw_data if isinstance(dup.raw_data, dict) else {}
            raw = {**raw, "duplicate_of": str(winner.id)}
            dup.raw_data = raw
            duplicates += 1

    await db.commit()
    return {
        "processed": processed,
        "invalid_url": invalid_url,
        "emails_cleared": emails_cleared,
        "company_normalized": company_normalized,
        "incomplete_profiles": incomplete_profiles,
        "duplicates": duplicates,
    }
