import random
import time


def human_delay(min_s: float = 0.6, max_s: float = 2.2) -> None:
    time.sleep(random.uniform(min_s, max_s))


def jitter_ms(base_ms: int, jitter_ms: int = 250) -> int:
    return max(0, base_ms + random.randint(-jitter_ms, jitter_ms))


def chromium_args() -> list[str]:
    return [
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-infobars",
        "--disable-notifications",
    ]
