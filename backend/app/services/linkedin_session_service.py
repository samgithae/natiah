from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from playwright.async_api import BrowserContext, Page
from jose import jwt

from app.core.config import settings


@dataclass
class SessionCheckResult:
    status: str
    detail: str | None = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _detect_captcha_text(content: str) -> bool:
    hay = (content or "").lower()
    triggers = [
        "captcha",
        "security verification",
        "verify you’re a person",
        "verify you're a person",
        "challenge",
        "checkpoint",
        "please verify",
    ]
    return any(t in hay for t in triggers)


async def detect_captcha(page: Page) -> bool:
    url = (page.url or "").lower()
    if "/checkpoint/" in url or "captcha" in url or "challenge" in url:
        return True
    try:
        if await page.query_selector("input[name*='captcha'], iframe[src*='captcha'], iframe[title*='captcha']"):
            return True
    except Exception:
        pass
    try:
        text = await page.inner_text("body")
        return _detect_captcha_text(text)
    except Exception:
        return False


async def has_linkedin_session_cookie(context: BrowserContext) -> bool:
    try:
        cookies = await context.cookies()
    except Exception:
        return False
    for c in cookies:
        name = str(c.get("name") or "")
        domain = str(c.get("domain") or "")
        if name == "li_at" and "linkedin" in domain:
            return True
    return False


async def check_authenticated(page: Page, context: BrowserContext) -> SessionCheckResult:
    if await detect_captcha(page):
        return SessionCheckResult(status="captcha")
    url = (page.url or "").lower()
    if "linkedin.com/login" in url or "/uas/login" in url or "/checkpoint/" in url:
        return SessionCheckResult(status="expired")
    if await has_linkedin_session_cookie(context):
        return SessionCheckResult(status="connected")
    return SessionCheckResult(status="expired")


async def open_and_verify(context: BrowserContext, page: Page) -> SessionCheckResult:
    try:
        await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
        await asyncio.sleep(0.5)
    except Exception:
        pass
    return await check_authenticated(page, context)


async def wait_for_manual_login(context: BrowserContext, page: Page, *, timeout_s: int = 300) -> SessionCheckResult:
    try:
        await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
    except Exception:
        pass

    end = _utc_now().timestamp() + float(timeout_s)
    while _utc_now().timestamp() < end:
        if await detect_captcha(page):
            return SessionCheckResult(status="captcha")
        if await has_linkedin_session_cookie(context):
            return SessionCheckResult(status="connected")
        try:
            url = (page.url or "").lower()
            if re.search(r"linkedin\.com/(feed|in|sales)", url) and "login" not in url:
                chk = await check_authenticated(page, context)
                if chk.status == "connected":
                    return chk
        except Exception:
            pass
        await asyncio.sleep(2.0)
    return SessionCheckResult(status="expired", detail="timeout_waiting_for_login")


def create_connect_token(*, user_id: str, account_id: str, expires_minutes: int = 15) -> str:
    exp = _utc_now() + timedelta(minutes=int(expires_minutes))
    payload = {"sub": user_id, "acc": account_id, "typ": "li_connect", "exp": exp}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_connect_token(token: str) -> dict:
    data = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if data.get("typ") != "li_connect":
        raise ValueError("invalid_token_type")
    return data


async def connect_with_li_at_cookie(
    *,
    context: BrowserContext,
    page: Page,
    li_at: str,
) -> SessionCheckResult:
    v = (li_at or "").strip()
    if not v:
        return SessionCheckResult(status="expired", detail="missing_cookie")
    await context.add_cookies(
        [
            {
                "name": "li_at",
                "value": v,
                "domain": ".linkedin.com",
                "path": "/",
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax",
            }
        ]
    )
    return await open_and_verify(context, page)
