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
            raise RuntimeError("LinkedIn login required for this account session")
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

        connect_btn = await page.query_selector("button:has-text('Connect')")
        if not connect_btn:
            connect_btn = await page.query_selector("button[aria-label*='Connect']")

        if not connect_btn:
            more_btn = await page.query_selector("button:has-text('More')")
            if more_btn:
                await more_btn.click()
                human_delay(0.4, 0.9)
                menu_item = await page.query_selector("[role='menu'] >> text=Connect")
                if menu_item:
                    await menu_item.click()
                    human_delay(0.4, 0.9)
        else:
            await connect_btn.click()
            human_delay(0.4, 0.9)

        add_note = await page.query_selector("button:has-text('Add a note')")
        if add_note and note and note.strip():
            await add_note.click()
            human_delay(0.3, 0.7)
            textarea = await page.query_selector("textarea")
            if not textarea:
                raise RuntimeError("Connection note textarea not found")
            await textarea.fill(note.strip())
            human_delay(0.4, 0.9)
            send_btn = await page.query_selector("button:has-text('Send')")
            if not send_btn:
                raise RuntimeError("Send button not found")
            await send_btn.click()
            human_delay(0.6, 1.2)
    finally:
        await page.close()


async def send_follow_up_message(context: BrowserContext, thread_url: str, message: str) -> None:
    page = await context.new_page()
    try:
        await page.goto(thread_url, wait_until="domcontentloaded")
        await random_mouse_jitter(page)
        human_delay(0.8, 1.6)
        target = await page.query_selector("div[role='textbox']")
        if target:
            await target.click()
            human_delay(0.2, 0.5)
            await target.type(message)
        else:
            textarea = await page.query_selector("textarea")
            if not textarea:
                raise RuntimeError("Message input not found")
            await type_like_human(page, "textarea", message)
        human_delay(0.3, 0.7)
        send_btn = await page.query_selector("button:has-text('Send')")
        if send_btn:
            await send_btn.click()
        else:
            await page.keyboard.press("Enter")
        human_delay(0.6, 1.2)
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
