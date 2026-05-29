from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_settings import AppSettings
from app.models.automation_state import AutomationAccountDayStats, AutomationAccountState
from app.models.linkedin_account import LinkedInAccount

from automation.anti_detection_system import AntiDetectionManager, working_window_utc, working_window_utc_custom


@dataclass
class RotationCandidate:
    account: LinkedInAccount
    health_score: int
    weight: float


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _get_stats_zero() -> dict[str, int]:
    return {"connections_sent": 0, "messages_sent": 0, "profile_visits": 0, "failures": 0}


def _compute_health_score(
    *,
    account: LinkedInAccount,
    state: AutomationAccountState | None,
    stats: AutomationAccountDayStats | None,
    now: datetime,
) -> int:
    risk = int(state.risk_score or 0) if state else 0
    failures = int(stats.failures or 0) if stats else 0
    last_captcha_at = state.last_captcha_at if state else None

    score = 100
    score -= min(80, risk * 8)
    score -= min(60, failures * 15)

    if last_captcha_at:
        age = now - last_captcha_at
        if age <= timedelta(days=2):
            score -= 50
        elif age <= timedelta(days=7):
            score -= 25

    if account.last_active:
        try:
            age = now - account.last_active
            if age <= timedelta(minutes=10):
                score -= 15
        except Exception:
            pass

    if (account.status or "").lower() == "inactive":
        score -= 30

    return max(1, min(100, score))


def _is_allowed_now(
    *,
    account: LinkedInAccount,
    state: AutomationAccountState | None,
    stats: AutomationAccountDayStats | None,
    job_type: str,
    now: datetime,
    app_settings: AppSettings | None,
) -> bool:
    if app_settings:
        start, end = working_window_utc_custom(
            account.id,
            day=now.date(),
            start_min=int(app_settings.work_start_min_hour),
            start_max=int(app_settings.work_start_max_hour),
            end_min=int(app_settings.work_end_min_hour),
            end_max=int(app_settings.work_end_max_hour),
        )
    else:
        start, end = working_window_utc(account.id, now.date())
    if now < start or now > end:
        return False

    if state and state.paused_until and state.paused_until > now:
        return False
    if state and state.cooldown_until and state.cooldown_until > now:
        return False

    s = stats
    connections_sent = int(s.connections_sent or 0) if s else 0
    messages_sent = int(s.messages_sent or 0) if s else 0
    profile_visits = int(s.profile_visits or 0) if s else 0

    total_actions = connections_sent + messages_sent + profile_visits
    if account.daily_limit and total_actions >= int(account.daily_limit):
        return False

    max_connections = int(app_settings.max_connections_per_day) if app_settings else AntiDetectionManager.MAX_CONNECTIONS_PER_DAY
    max_messages = int(app_settings.max_messages_per_day) if app_settings else AntiDetectionManager.MAX_MESSAGES_PER_DAY
    max_visits = int(app_settings.max_profile_visits_per_day) if app_settings else AntiDetectionManager.MAX_PROFILE_VISITS_PER_DAY

    if job_type == "CONNECT" and connections_sent >= max_connections:
        return False
    if job_type == "SEND_FOLLOW_UP" and messages_sent >= max_messages:
        return False
    if job_type == "VISIT_PROFILE" and profile_visits >= max_visits:
        return False

    return True


def _capacity_weight(
    *,
    account: LinkedInAccount,
    stats: AutomationAccountDayStats | None,
    job_type: str,
    app_settings: AppSettings | None,
) -> float:
    s = stats
    connections_sent = int(s.connections_sent or 0) if s else 0
    messages_sent = int(s.messages_sent or 0) if s else 0
    profile_visits = int(s.profile_visits or 0) if s else 0

    if account.daily_limit and int(account.daily_limit) > 0:
        total_actions = connections_sent + messages_sent + profile_visits
        remaining_total = max(0, int(account.daily_limit) - total_actions)
        total_factor = remaining_total / float(account.daily_limit)
    else:
        total_factor = 1.0

    max_connections = int(app_settings.max_connections_per_day) if app_settings else AntiDetectionManager.MAX_CONNECTIONS_PER_DAY
    max_messages = int(app_settings.max_messages_per_day) if app_settings else AntiDetectionManager.MAX_MESSAGES_PER_DAY
    max_visits = int(app_settings.max_profile_visits_per_day) if app_settings else AntiDetectionManager.MAX_PROFILE_VISITS_PER_DAY

    if job_type == "CONNECT":
        denom = float(max(1, max_connections))
        remaining = max(0, max_connections - connections_sent)
        per_action_factor = remaining / denom
    elif job_type == "SEND_FOLLOW_UP":
        denom = float(max(1, max_messages))
        remaining = max(0, max_messages - messages_sent)
        per_action_factor = remaining / denom
    elif job_type == "VISIT_PROFILE":
        denom = float(max(1, max_visits))
        remaining = max(0, max_visits - profile_visits)
        per_action_factor = remaining / denom
    else:
        per_action_factor = 1.0

    return max(0.05, min(1.0, total_factor * per_action_factor))


async def pick_account_for_job(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    job_type: str,
    exclude_account_ids: set[uuid.UUID] | None = None,
) -> uuid.UUID | None:
    exclude_account_ids = exclude_account_ids or set()
    now = _utc_now()

    res = await db.execute(select(LinkedInAccount).where(LinkedInAccount.user_id == user_id))
    accounts = [a for a in res.scalars().all() if a.id not in exclude_account_ids]
    if not accounts:
        return None

    settings_res = await db.execute(select(AppSettings).where(AppSettings.user_id == user_id))
    app_settings = settings_res.scalar_one_or_none()

    states_res = await db.execute(
        select(AutomationAccountState).where(AutomationAccountState.account_id.in_([a.id for a in accounts]))
    )
    states = {s.account_id: s for s in states_res.scalars().all()}

    stats_res = await db.execute(
        select(AutomationAccountDayStats).where(
            AutomationAccountDayStats.account_id.in_([a.id for a in accounts]),
            AutomationAccountDayStats.day == now.date(),
        )
    )
    day_stats = {s.account_id: s for s in stats_res.scalars().all()}

    candidates: list[RotationCandidate] = []
    for a in accounts:
        st = states.get(a.id)
        ds = day_stats.get(a.id)
        if not _is_allowed_now(account=a, state=st, stats=ds, job_type=job_type, now=now, app_settings=app_settings):
            continue

        health = _compute_health_score(account=a, state=st, stats=ds, now=now)
        cap = _capacity_weight(account=a, stats=ds, job_type=job_type, app_settings=app_settings)
        weight = max(0.1, float(health) * cap)
        candidates.append(RotationCandidate(account=a, health_score=health, weight=weight))

    if not candidates:
        return None

    total = sum(c.weight for c in candidates)
    r = random.random() * total
    running = 0.0
    for c in sorted(candidates, key=lambda x: x.health_score, reverse=True):
        running += c.weight
        if r <= running:
            return c.account.id
    return candidates[0].account.id
