"""Test helper: put a learner on a plan.

The spoken interview is a paid feature, so a suite that exercises it has to
give its learner a plan that includes it -- exactly as a real user taking the
spoken test would have. Weakening the guard so the old tests pass would be
testing a product nobody ships.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select, update

from db.session import SessionLocal
from models.user import User


def grant_plan(email: str, plan: str = "unlimited") -> None:
    """Set a registered learner's plan. Synchronous, for use inside a suite."""

    async def _apply() -> None:
        async with SessionLocal() as session:
            user = await session.scalar(select(User).where(User.email == email))
            if user is None:
                return
            await session.execute(
                update(User).where(User.id == user.id).values(plan=plan)
            )
            await session.commit()

    asyncio.run(_apply())
