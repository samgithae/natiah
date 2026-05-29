import json

from playwright.async_api import Browser, BrowserContext, async_playwright


async def launch_browser(headless: bool = True, slow_mo_ms: int = 0) -> Browser:
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=headless, slow_mo=slow_mo_ms)
    browser._natiah_playwright = p
    return browser


async def close_browser(browser: Browser) -> None:
    p = getattr(browser, "_natiah_playwright", None)
    await browser.close()
    if p:
        await p.stop()


async def new_context(browser: Browser, cookies_json: str | None) -> BrowserContext:
    context = await browser.new_context(
        viewport={"width": 1280, "height": 800},
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        locale="en-US",
    )
    if cookies_json:
        cookies = json.loads(cookies_json)
        if isinstance(cookies, dict) and "cookies" in cookies:
            cookies = cookies["cookies"]
        if isinstance(cookies, list):
            await context.add_cookies(cookies)
    return context


async def launch_persistent_context(
    user_data_dir: str,
    *,
    headless: bool = False,
    slow_mo_ms: int = 0,
    args: list[str] | None = None,
    proxy: dict | None = None,
) -> BrowserContext:
    p = await async_playwright().start()
    context = await p.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        headless=headless,
        slow_mo=slow_mo_ms,
        args=args or [],
        proxy=proxy,
        viewport={"width": 1280, "height": 800},
        locale="en-US",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    )
    context._natiah_playwright = p
    return context


async def close_context(context: BrowserContext) -> None:
    p = getattr(context, "_natiah_playwright", None)
    await context.close()
    if p:
        await p.stop()
