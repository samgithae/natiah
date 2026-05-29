from __future__ import annotations

from dataclasses import dataclass

from playwright.async_api import BrowserContext, Page, async_playwright


@dataclass
class PlaywrightContext:
    context: BrowserContext
    page: Page


async def launch_persistent_context(
    *,
    user_data_dir: str,
    headless: bool,
    slow_mo_ms: int = 0,
    args: list[str] | None = None,
    proxy: dict | None = None,
) -> PlaywrightContext:
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
    page = context.pages[0] if context.pages else await context.new_page()
    return PlaywrightContext(context=context, page=page)


async def close_persistent_context(ctx: BrowserContext) -> None:
    p = getattr(ctx, "_natiah_playwright", None)
    await ctx.close()
    if p:
        await p.stop()
