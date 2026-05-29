import asyncio
import os

from app.db.session import async_session_maker
from app.core.security import hash_password
from app.services.auth import create_user, get_user_by_email


async def _run() -> None:
    email = (os.environ.get("NATIAH_ADMIN_EMAIL") or "").strip().lower()
    password = os.environ.get("NATIAH_ADMIN_PASSWORD") or ""
    force = (os.environ.get("NATIAH_ADMIN_FORCE") or "").strip().lower() in {"1", "true", "yes"}
    if not email or not password:
        raise RuntimeError("Set NATIAH_ADMIN_EMAIL and NATIAH_ADMIN_PASSWORD")

    async with async_session_maker() as db:
        existing = await get_user_by_email(db, email)
        if existing:
            if force:
                existing.hashed_password = hash_password(password)
                await db.commit()
            return
        await create_user(db, email, password)


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
