from playwright.async_api import BrowserContext

from automation.anti_detection import human_delay


async def ensure_logged_in(context: BrowserContext) -> bool:
    page = await context.new_page()
    try:
        await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
        human_delay()
        if "login" in (page.url or ""):
            return False
        return True
    finally:
        await page.close()


async def visit_profile(context: BrowserContext, profile_url: str) -> None:
    page = await context.new_page()
    try:
        await page.goto(profile_url, wait_until="domcontentloaded")
        human_delay(1.2, 3.0)
    finally:
        await page.close()


async def send_connection_request(
    context: BrowserContext,
    profile_url: str,
    note: str | None = None,
) -> None:
    page = await context.new_page()
    try:
        await page.goto(profile_url, wait_until="domcontentloaded")
        human_delay(1.0, 2.4)
    finally:
        await page.close()


async def send_message(context: BrowserContext, thread_url: str, message: str) -> None:
    page = await context.new_page()
    try:
        await page.goto(thread_url, wait_until="domcontentloaded")
        human_delay(1.0, 2.4)
    finally:
        await page.close()

