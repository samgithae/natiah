from __future__ import annotations

import asyncio
import logging
import os
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401
from app.db.session import async_session_maker
from app.models.app_settings import AppSettings
from app.models.linkedin_account import LinkedInAccount

from automation.actions import (
    ensure_logged_in,
    monitor_inbox,
    scrape_sales_navigator,
    send_connection_request,
    send_follow_up_message,
    visit_profile,
)
from automation.anti_detection import chromium_args
from automation.browser import close_context, launch_persistent_context
from automation.anti_detection_system import (
    AntiDetectionManager,
    CaptchaDetectedError,
    detect_captcha,
)
from automation.pg_queue import fetch_and_lock_next_job, mark_job_done, mark_job_failed, reschedule_job
from automation.rotation_engine import pick_account_for_job


def profile_dir_for_account(account: LinkedInAccount) -> str:
    if account.session_path:
        return account.session_path
    base = Path(__file__).resolve().parent / "profiles"
    return str(base / f"account_{str(account.id).replace('-', '')[:8]}")


async def get_account(db: AsyncSession, account_id: uuid.UUID) -> LinkedInAccount | None:
    res = await db.execute(select(LinkedInAccount).where(LinkedInAccount.id == account_id))
    return res.scalar_one_or_none()


def _normalize_url(u: str) -> str:
    v = (u or "").strip()
    if not v:
        return ""
    if "://" not in v:
        v = f"https://{v}"
    try:
        p = urlparse(v)
    except Exception:
        return v.lower().rstrip("/")
    host = (p.netloc or "").lower()
    path = (p.path or "").rstrip("/")
    return f"{host}{path}".lower()


def _payload_urls(payload: dict) -> list[str]:
    urls: list[str] = []
    for k in ("profile_url", "thread_url", "search_url", "linkedin_url"):
        v = payload.get(k)
        if isinstance(v, str) and v.strip():
            urls.append(v.strip())
    return urls


def _is_blacklisted(*, payload: dict, settings: AppSettings | None) -> bool:
    if not settings:
        return False
    urls = _payload_urls(payload)
    if not urls:
        return False
    blocked_domains = [str(d).strip().lower() for d in (settings.blacklist_domains or []) if str(d).strip()]
    blocked_urls = [str(u).strip().lower().rstrip("/") for u in (settings.blacklist_linkedin_urls or []) if str(u).strip()]

    for u in urls:
        norm = _normalize_url(u)
        if norm.lower().rstrip("/") in blocked_urls:
            return True
        try:
            host = urlparse(u if "://" in u else f"https://{u}").netloc.lower()
        except Exception:
            host = ""
        host = host[4:] if host.startswith("www.") else host
        if host and any(host == d or host.endswith(f".{d}") for d in blocked_domains):
            return True
    return False


async def run_once(context_cache: dict[str, object]) -> bool:
    async with async_session_maker() as db:
        try:
            job = await fetch_and_lock_next_job(db)
        except Exception:
            logging.getLogger("natiah").exception("Failed to fetch/lock next automation job")
            return True
        if not job:
            return False

        try:
            settings_res = await db.execute(select(AppSettings).where(AppSettings.user_id == job.user_id))
            settings = settings_res.scalar_one_or_none()

            account = await get_account(db, job.account_id)
            if not account:
                raise RuntimeError("LinkedIn account not found")

            manager = AntiDetectionManager()
            allow = await manager.allow_action(db, account.id, job.job_type)
            if not allow.allowed:
                alt = await pick_account_for_job(
                    db,
                    user_id=job.user_id,
                    job_type=job.job_type,
                    exclude_account_ids={job.account_id},
                )
                if alt:
                    account = await get_account(db, alt)
                    if not account:
                        when = allow.next_run_at or (job.run_at)
                        await reschedule_job(db, job.id, when, allow.reason or "not_allowed")
                        return True
                    job.account_id = alt
                    await db.commit()
                    allow2 = await manager.allow_action(db, account.id, job.job_type)
                    if not allow2.allowed:
                        when = allow2.next_run_at or (allow.next_run_at) or (job.run_at)
                        await reschedule_job(db, job.id, when, allow2.reason or "not_allowed")
                        return True
                else:
                    when = allow.next_run_at or (job.run_at)
                    await reschedule_job(db, job.id, when, allow.reason or "not_allowed")
                    return True

            payload = job.payload or {}
            job_type = job.job_type

            if _is_blacklisted(payload=payload, settings=settings):
                job.status = "done"
                job.last_error = "skipped_blacklist"
                await db.commit()
                return True

            key = str(account.id)
            ctx = context_cache.get(key)
            if ctx is None:
                user_data_dir = profile_dir_for_account(account)
                os.makedirs(user_data_dir, exist_ok=True)
                proxy = None
                if settings and settings.proxy_url:
                    proxy = {"server": settings.proxy_url}
                    if settings.proxy_username:
                        proxy["username"] = settings.proxy_username
                    if settings.proxy_password:
                        proxy["password"] = settings.proxy_password
                headless = (os.environ.get("PLAYWRIGHT_HEADLESS") or "").lower() in {"1", "true", "yes"}
                ctx = await launch_persistent_context(
                    user_data_dir,
                    headless=headless,
                    slow_mo_ms=0,
                    args=chromium_args(),
                    proxy=proxy,
                )
                context_cache[key] = ctx

            await ensure_logged_in(ctx)

            if job_type == "LOGIN":
                pass
            elif job_type == "VISIT_PROFILE":
                await visit_profile(ctx, payload["profile_url"])
            elif job_type == "CONNECT":
                await send_connection_request(ctx, payload["profile_url"], payload.get("note"))
            elif job_type == "SEND_FOLLOW_UP":
                await send_follow_up_message(ctx, payload["thread_url"], payload["message"])
            elif job_type == "MONITOR_INBOX":
                await monitor_inbox(ctx)
            elif job_type == "SCRAPE_SALES_NAVIGATOR":
                try:
                    scrape_timeout_s = float(os.environ.get("NATIAH_SCRAPE_TIMEOUT_S") or "240")
                except Exception:
                    scrape_timeout_s = 240.0
                await asyncio.wait_for(
                    scrape_sales_navigator(
                        context=ctx,
                        db=db,
                        account_id=job.account_id,
                        search_url=payload["search_url"],
                        limit=int(payload.get("limit") or 50),
                    ),
                    timeout=scrape_timeout_s,
                )
            else:
                raise RuntimeError(f"Unknown job_type: {job_type}")

            pages = ctx.pages
            if pages:
                if await detect_captcha(pages[-1]):
                    raise CaptchaDetectedError("Captcha detected")

            if job_type in {"CONNECT", "SEND_FOLLOW_UP", "VISIT_PROFILE"}:
                await manager.record_success(db, account.id, job_type)
            account.last_active = datetime.now(timezone.utc)
            await db.commit()
            await mark_job_done(db, job.id)
            return True
        except CaptchaDetectedError as e:
            logging.getLogger("natiah").exception("Automation job failed (captcha): %s", str(job.id))
            manager = AntiDetectionManager()
            await manager.record_failure(db, job.account_id, captcha=True)
            await mark_job_failed(db, job.id, traceback.format_exc())
            return True
        except Exception as e:
            logging.getLogger("natiah").exception("Automation job failed: %s", str(job.id))
            manager = AntiDetectionManager()
            await manager.record_failure(db, job.account_id, captcha=False)
            await mark_job_failed(db, job.id, traceback.format_exc())
            return True


async def run_loop() -> None:
    context_cache: dict[str, object] = {}
    idle_sleep_s = float(os.environ.get("NATIAH_PGQ_IDLE_SLEEP_S") or "1.5")
    while True:
        did = await run_once(context_cache)
        if not did:
            await asyncio.sleep(idle_sleep_s)


def main() -> None:
    asyncio.run(run_loop())


if __name__ == "__main__":
    main()
