from __future__ import annotations

import hashlib
import os
import random
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from playwright.async_api import Page
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_settings import AppSettings
from app.models.linkedin_account import LinkedInAccount
from app.models.automation_state import AutomationAccountDayStats, AutomationAccountState


class CaptchaDetectedError(RuntimeError):
    pass


@dataclass
class AllowResult:
    allowed: bool
    next_run_at: datetime | None = None
    reason: str | None = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _today_utc() -> date:
    return _utc_now().date()


def _stable_random(account_id: uuid.UUID, day: date) -> random.Random:
    raw = f"{account_id}:{day.isoformat()}".encode("utf-8")
    seed = int(hashlib.sha256(raw).hexdigest()[:16], 16)
    return random.Random(seed)


def working_window_utc(account_id: uuid.UUID, day: date | None = None) -> tuple[datetime, datetime]:
    day = day or _today_utc()
    r = _stable_random(account_id, day)
    start_min = int(os.environ.get("NATIAH_WORK_START_MIN_HOUR") or "8")
    start_max = int(os.environ.get("NATIAH_WORK_START_MAX_HOUR") or "11")
    end_min = int(os.environ.get("NATIAH_WORK_END_MIN_HOUR") or "16")
    end_max = int(os.environ.get("NATIAH_WORK_END_MAX_HOUR") or "21")
    start_h = r.randint(min(start_min, start_max), max(start_min, start_max))
    end_h = r.randint(min(end_min, end_max), max(end_min, end_max))
    if end_h <= start_h + 3:
        end_h = min(23, start_h + 6)
    start = datetime.combine(day, time(start_h, r.randint(0, 59)), tzinfo=timezone.utc)
    end = datetime.combine(day, time(end_h, r.randint(0, 59)), tzinfo=timezone.utc)
    return start, end


def working_window_utc_custom(
    account_id: uuid.UUID,
    *,
    day: date,
    start_min: int,
    start_max: int,
    end_min: int,
    end_max: int,
) -> tuple[datetime, datetime]:
    r = _stable_random(account_id, day)
    start_h = r.randint(min(start_min, start_max), max(start_min, start_max))
    end_h = r.randint(min(end_min, end_max), max(end_min, end_max))
    if end_h <= start_h + 3:
        end_h = min(23, start_h + 6)
    start = datetime.combine(day, time(start_h, r.randint(0, 59)), tzinfo=timezone.utc)
    end = datetime.combine(day, time(end_h, r.randint(0, 59)), tzinfo=timezone.utc)
    return start, end


def detect_captcha_text(content: str) -> bool:
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
        return detect_captcha_text(text)
    except Exception:
        return False


async def type_like_human(page: Page, selector: str, text: str) -> None:
    await page.click(selector)
    r = random.Random()
    for ch in text:
        await page.keyboard.type(ch, delay=r.randint(35, 120))
        if r.random() < 0.05:
            await page.wait_for_timeout(r.randint(120, 420))


class AntiDetectionManager:
    MAX_CONNECTIONS_PER_DAY = 30
    MAX_MESSAGES_PER_DAY = 60
    MAX_PROFILE_VISITS_PER_DAY = 80

    def __init__(self, *, risk_pause_hours: int = 24, failure_cooldown_min: int = 90):
        self.risk_pause_hours = risk_pause_hours
        self.failure_cooldown_min = failure_cooldown_min

    async def _get_or_create_state(self, db: AsyncSession, account_id: uuid.UUID) -> AutomationAccountState:
        state = await db.get(AutomationAccountState, account_id)
        if state:
            return state
        stmt = (
            insert(AutomationAccountState)
            .values(account_id=account_id, risk_score=0)
            .on_conflict_do_nothing()
            .returning(AutomationAccountState.account_id)
        )
        await db.execute(stmt)
        await db.commit()
        state = await db.get(AutomationAccountState, account_id)
        return state

    async def _get_or_create_today_stats(
        self, db: AsyncSession, account_id: uuid.UUID, day: date
    ) -> AutomationAccountDayStats:
        stmt = (
            insert(AutomationAccountDayStats)
            .values(account_id=account_id, day=day)
            .on_conflict_do_nothing(constraint="uq_auto_stats_account_day")
            .returning(AutomationAccountDayStats.id)
        )
        await db.execute(stmt)
        await db.commit()
        res = await db.execute(
            select(AutomationAccountDayStats).where(
                AutomationAccountDayStats.account_id == account_id, AutomationAccountDayStats.day == day
            )
        )
        return res.scalar_one()

    async def allow_action(self, db: AsyncSession, account_id: uuid.UUID, action: str) -> AllowResult:
        now = _utc_now()
        acct = await db.get(LinkedInAccount, account_id)
        app_settings: AppSettings | None = None
        if acct:
            res = await db.execute(select(AppSettings).where(AppSettings.user_id == acct.user_id))
            app_settings = res.scalar_one_or_none()

        state = await self._get_or_create_state(db, account_id)
        if state.paused_until and state.paused_until > now:
            return AllowResult(False, next_run_at=state.paused_until, reason="paused")
        if state.cooldown_until and state.cooldown_until > now:
            return AllowResult(False, next_run_at=state.cooldown_until, reason="cooldown")

        if action != "SCRAPE_SALES_NAVIGATOR":
            if app_settings:
                start, end = working_window_utc_custom(
                    account_id,
                    day=now.date(),
                    start_min=int(app_settings.work_start_min_hour),
                    start_max=int(app_settings.work_start_max_hour),
                    end_min=int(app_settings.work_end_min_hour),
                    end_max=int(app_settings.work_end_max_hour),
                )
            else:
                start, end = working_window_utc(account_id, now.date())
            if now < start:
                return AllowResult(False, next_run_at=start, reason="outside_working_hours")
            if now > end:
                if app_settings:
                    next_start, _ = working_window_utc_custom(
                        account_id,
                        day=now.date() + timedelta(days=1),
                        start_min=int(app_settings.work_start_min_hour),
                        start_max=int(app_settings.work_start_max_hour),
                        end_min=int(app_settings.work_end_min_hour),
                        end_max=int(app_settings.work_end_max_hour),
                    )
                else:
                    next_start, _ = working_window_utc(account_id, now.date() + timedelta(days=1))
                return AllowResult(False, next_run_at=next_start, reason="outside_working_hours")

        if action == "SCRAPE_SALES_NAVIGATOR":
            return AllowResult(True)

        stats = await self._get_or_create_today_stats(db, account_id, now.date())
        raw_connections = int(app_settings.max_connections_per_day) if app_settings else self.MAX_CONNECTIONS_PER_DAY
        raw_messages = int(app_settings.max_messages_per_day) if app_settings else self.MAX_MESSAGES_PER_DAY
        raw_visits = int(app_settings.max_profile_visits_per_day) if app_settings else self.MAX_PROFILE_VISITS_PER_DAY

        try:
            safety = float(os.environ.get("NATIAH_SAFETY_FACTOR") or "0.5")
        except Exception:
            safety = 0.5
        safety = min(1.0, max(0.1, safety))

        max_connections = max(1, int(raw_connections * safety))
        max_messages = max(1, int(raw_messages * safety))
        max_visits = max(1, int(raw_visits * safety))

        if action == "CONNECT" and stats.connections_sent >= max_connections:
            if app_settings:
                next_start, _ = working_window_utc_custom(
                    account_id,
                    day=now.date() + timedelta(days=1),
                    start_min=int(app_settings.work_start_min_hour),
                    start_max=int(app_settings.work_start_max_hour),
                    end_min=int(app_settings.work_end_min_hour),
                    end_max=int(app_settings.work_end_max_hour),
                )
            else:
                next_start, _ = working_window_utc(account_id, now.date() + timedelta(days=1))
            await self.set_cooldown(db, account_id, next_start, risk_delta=1)
            return AllowResult(False, next_run_at=next_start, reason="limit_connections")
        if action == "SEND_FOLLOW_UP" and stats.messages_sent >= max_messages:
            if app_settings:
                next_start, _ = working_window_utc_custom(
                    account_id,
                    day=now.date() + timedelta(days=1),
                    start_min=int(app_settings.work_start_min_hour),
                    start_max=int(app_settings.work_start_max_hour),
                    end_min=int(app_settings.work_end_min_hour),
                    end_max=int(app_settings.work_end_max_hour),
                )
            else:
                next_start, _ = working_window_utc(account_id, now.date() + timedelta(days=1))
            await self.set_cooldown(db, account_id, next_start, risk_delta=1)
            return AllowResult(False, next_run_at=next_start, reason="limit_messages")
        if action == "VISIT_PROFILE" and stats.profile_visits >= max_visits:
            if app_settings:
                next_start, _ = working_window_utc_custom(
                    account_id,
                    day=now.date() + timedelta(days=1),
                    start_min=int(app_settings.work_start_min_hour),
                    start_max=int(app_settings.work_start_max_hour),
                    end_min=int(app_settings.work_end_min_hour),
                    end_max=int(app_settings.work_end_max_hour),
                )
            else:
                next_start, _ = working_window_utc(account_id, now.date() + timedelta(days=1))
            await self.set_cooldown(db, account_id, next_start, risk_delta=1)
            return AllowResult(False, next_run_at=next_start, reason="limit_visits")

        return AllowResult(True)

    async def record_success(self, db: AsyncSession, account_id: uuid.UUID, action: str) -> None:
        day = _today_utc()
        stats = await self._get_or_create_today_stats(db, account_id, day)
        if action == "CONNECT":
            stats.connections_sent += 1
        elif action == "SEND_FOLLOW_UP":
            stats.messages_sent += 1
        elif action == "VISIT_PROFILE":
            stats.profile_visits += 1
        if stats.failures > 0:
            stats.failures = max(0, stats.failures - 1)
        state = await self._get_or_create_state(db, account_id)
        if state.risk_score > 0:
            state.risk_score = max(0, state.risk_score - 1)
        await db.commit()

    async def record_failure(self, db: AsyncSession, account_id: uuid.UUID, *, captcha: bool) -> None:
        now = _utc_now()
        stats = await self._get_or_create_today_stats(db, account_id, now.date())
        stats.failures += 1
        state = await self._get_or_create_state(db, account_id)
        state.risk_score += 3 if captcha else 1
        if captcha:
            state.last_captcha_at = now
            state.paused_until = now + timedelta(hours=self.risk_pause_hours)
        elif stats.failures >= 3:
            state.cooldown_until = now + timedelta(minutes=self.failure_cooldown_min)
        if state.risk_score >= 12 and (not state.paused_until or state.paused_until <= now):
            state.paused_until = now + timedelta(hours=self.risk_pause_hours)
        await db.commit()

    async def set_cooldown(self, db: AsyncSession, account_id: uuid.UUID, until: datetime, risk_delta: int = 0) -> None:
        state = await self._get_or_create_state(db, account_id)
        state.cooldown_until = until
        state.risk_score = max(0, int(state.risk_score or 0) + risk_delta)
        await db.commit()
