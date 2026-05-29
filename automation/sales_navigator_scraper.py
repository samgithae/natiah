from __future__ import annotations

import asyncio
import random
import re
import uuid
from dataclasses import dataclass
from urllib.parse import urljoin

from playwright.async_api import BrowserContext, Page
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead

from automation.human import human_delay, random_mouse_jitter, random_scroll


LINKEDIN_BASE = "https://www.linkedin.com"


@dataclass
class ScrapedLead:
    linkedin_url: str
    first_name: str | None = None
    last_name: str | None = None
    job_title: str | None = None
    company: str | None = None
    location: str | None = None


def _normalize_linkedin_url(href: str) -> str:
    href = href.strip()
    if href.startswith("/"):
        return urljoin(LINKEDIN_BASE, href)
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return urljoin(LINKEDIN_BASE, f"/{href.lstrip('/')}")


def _split_name(full: str) -> tuple[str | None, str | None]:
    full = (full or "").strip()
    if not full:
        return None, None
    parts = [p for p in re.split(r"\s+", full) if p]
    if len(parts) == 1:
        return parts[0], None
    return parts[0], " ".join(parts[1:])


async def _retry(coro_factory, *, attempts: int = 3, base_delay_s: float = 1.0):
    last = None
    for i in range(attempts):
        try:
            return await coro_factory()
        except Exception as e:
            last = e
            await asyncio.sleep(base_delay_s * (2**i) + random.uniform(0, 0.6))
    raise last  # type: ignore[misc]


class SalesNavigatorScraper:
    def __init__(self, context: BrowserContext):
        self.context = context

    async def _goto(self, page: Page, url: str) -> None:
        await _retry(lambda: page.goto(url, wait_until="domcontentloaded"), attempts=3)

    async def _collect_cards(self, page: Page) -> list[dict]:
        js = """
        (root) => {
          const cards = [];
          const rows = Array.from(document.querySelectorAll('li, div')).slice(0, 2000);
          for (const el of rows) {
            const a = el.querySelector && el.querySelector("a[href*='/in/'], a[href*='linkedin.com/in/']");
            if (!a) continue;
            const href = a.getAttribute("href") || "";
            const text = (el.innerText || "").trim();
            if (!text) continue;
            cards.push({ href, text });
          }
          return cards;
        }
        """
        return await page.evaluate(js, None)

    def _parse_card(self, card: dict) -> ScrapedLead | None:
        href = (card.get("href") or "").strip()
        text = (card.get("text") or "").strip()
        if not href or "/in/" not in href:
            return None

        url = _normalize_linkedin_url(href.split("?")[0])

        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if not lines:
            return None

        first_name, last_name = _split_name(lines[0])

        job_title = None
        company = None
        location = None

        if len(lines) >= 2:
            job_title = lines[1]
        if len(lines) >= 3:
            company = lines[2]
        if len(lines) >= 4:
            location = lines[3]

        return ScrapedLead(
            linkedin_url=url,
            first_name=first_name,
            last_name=last_name,
            job_title=job_title,
            company=company,
            location=location,
        )

    async def _infinite_scroll(self, page: Page, *, max_rounds: int = 12) -> None:
        prev = 0
        for _ in range(max_rounds):
            cards = await self._collect_cards(page)
            cur = len(cards)
            if cur <= prev:
                break
            prev = cur
            await random_scroll(page, 2, 4)
            await random_mouse_jitter(page)
            human_delay(0.4, 1.2)

    async def _click_next(self, page: Page) -> bool:
        selectors = [
            "button[aria-label='Next']",
            "button[aria-label*='Next']",
            "button:has-text('Next')",
            "a[aria-label='Next']",
            "a:has-text('Next')",
        ]
        for sel in selectors:
            handle = await page.query_selector(sel)
            if handle:
                try:
                    await _retry(lambda: handle.click(), attempts=2)
                    await page.wait_for_timeout(random.randint(700, 1400))
                    return True
                except Exception:
                    continue
        return False

    async def scrape_search_results(
        self,
        *,
        db: AsyncSession,
        account_id: uuid.UUID,
        search_url: str,
        max_pages: int = 10,
        max_leads: int = 200,
    ) -> dict:
        page = await self.context.new_page()
        try:
            await self._goto(page, search_url)
            await random_mouse_jitter(page)

            seen: set[str] = set()
            created_or_updated = 0

            for _ in range(max_pages):
                await self._infinite_scroll(page, max_rounds=10)
                cards = await self._collect_cards(page)
                random.shuffle(cards)
                for c in cards:
                    lead = self._parse_card(c)
                    if not lead:
                        continue
                    if lead.linkedin_url in seen:
                        continue
                    seen.add(lead.linkedin_url)

                    stmt = (
                        insert(Lead)
                        .values(
                            account_id=account_id,
                            linkedin_url=lead.linkedin_url,
                            first_name=lead.first_name,
                            last_name=lead.last_name,
                            company=lead.company,
                            job_title=lead.job_title,
                            status="new",
                            raw_data={
                                "location": lead.location,
                                "source": "sales_navigator",
                                "search_url": search_url,
                            },
                        )
                        .on_conflict_do_update(
                            constraint="uq_leads_account_linkedin",
                            set_={
                                "first_name": lead.first_name,
                                "last_name": lead.last_name,
                                "company": lead.company,
                                "job_title": lead.job_title,
                                "raw_data": {
                                    "location": lead.location,
                                    "source": "sales_navigator",
                                    "search_url": search_url,
                                },
                            },
                        )
                        .returning(Lead.id)
                    )
                    res = await db.execute(stmt)
                    if res.scalar_one_or_none():
                        created_or_updated += 1
                    if created_or_updated % 10 == 0:
                        await db.commit()
                    if random.random() < 0.12:
                        human_delay(0.2, 0.8)

                    if len(seen) >= max_leads:
                        break
                await db.commit()
                if len(seen) >= max_leads:
                    break
                moved = await self._click_next(page)
                if not moved:
                    break
                human_delay(1.0, 2.2)

            return {"scraped": len(seen), "created_or_updated": created_or_updated}
        finally:
            await page.close()
