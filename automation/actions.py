from __future__ import annotations

import uuid

from playwright.async_api import BrowserContext
from sqlalchemy.ext.asyncio import AsyncSession

from automation.human import human_delay, random_mouse_jitter, random_scroll
from automation.anti_detection_system import type_like_human
from automation.sales_navigator_scraper import SalesNavigatorScraper


async def ensure_logged_in(context: BrowserContext, timeout_ms: int = 5 * 60 * 1000) -> bool:
    page = await context.new_page()
    try:
        await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
        await random_mouse_jitter(page)
        await random_scroll(page)
        if "login" in (page.url or ""):
            await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
            await page.wait_for_url("**/feed/**", timeout=timeout_ms)
        return True
    finally:
        await page.close()


async def visit_profile(context: BrowserContext, profile_url: str) -> None:
    page = await context.new_page()
    try:
        await page.goto(profile_url, wait_until="domcontentloaded")
        await random_mouse_jitter(page)
        await random_scroll(page, 2, 5)
        human_delay(1.0, 2.5)
    finally:
        await page.close()


async def send_connection_request(context: BrowserContext, profile_url: str, note: str | None = None) -> None:
    page = await context.new_page()
    try:
        await page.goto(profile_url, wait_until="domcontentloaded")
        await random_mouse_jitter(page)
        await random_scroll(page, 1, 3)
        human_delay(0.8, 1.6)
    finally:
        await page.close()


async def send_follow_up_message(context: BrowserContext, thread_url: str, message: str) -> None:
    page = await context.new_page()
    try:
        await page.goto(thread_url, wait_until="domcontentloaded")
        await random_mouse_jitter(page)
        human_delay(0.8, 1.6)
        await type_like_human(page, "textarea", message)
    finally:
        await page.close()


async def monitor_inbox(context: BrowserContext) -> dict:
    page = await context.new_page()
    try:
        await page.goto("https://www.linkedin.com/messaging/", wait_until="domcontentloaded")
        await random_mouse_jitter(page)
        human_delay(0.8, 1.4)
        return {"ok": True}
    finally:
        await page.close()


async def scrape_sales_navigator(
    *,
    context: BrowserContext,
    db: AsyncSession,
    account_id: uuid.UUID,
    search_url: str,
    limit: int = 50,
) -> dict:
    scraper = SalesNavigatorScraper(context)
    return await scraper.scrape_search_results(
        db=db,
        account_id=account_id,
        search_url=search_url,
        max_pages=10,
        max_leads=limit,
    )
