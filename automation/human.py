import random
import time

from playwright.async_api import Page


def human_delay(min_s: float = 0.4, max_s: float = 1.6) -> None:
    time.sleep(random.uniform(min_s, max_s))


def jitter_ms(base_ms: int, jitter: int = 250) -> int:
    return max(0, base_ms + random.randint(-jitter, jitter))


async def random_scroll(page: Page, min_steps: int = 1, max_steps: int = 3) -> None:
    steps = random.randint(min_steps, max_steps)
    for _ in range(steps):
        delta = random.randint(200, 900)
        await page.mouse.wheel(0, delta)
        human_delay(0.2, 0.8)


async def random_mouse_jitter(page: Page, moves: int | None = None) -> None:
    moves = moves if moves is not None else random.randint(3, 8)
    box = page.viewport_size
    if not box:
        return
    w, h = box["width"], box["height"]
    x = random.randint(20, max(20, w - 20))
    y = random.randint(20, max(20, h - 20))
    for _ in range(moves):
        x2 = max(0, min(w, x + random.randint(-120, 120)))
        y2 = max(0, min(h, y + random.randint(-80, 80)))
        await page.mouse.move(x2, y2, steps=random.randint(5, 18))
        human_delay(0.05, 0.25)
        x, y = x2, y2
