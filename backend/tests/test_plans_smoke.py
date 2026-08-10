"""Smoke test: plans and usage limits.

Limits exist because AI calls cost real money and nothing previously stopped
one learner spending all of it. The assertions are about where the line sits:
what still works at the limit, what does not, and what a learner is told.

A limit that locks someone out of work they have already done, or that only
announces itself at the moment of refusal, is a worse product than no limit.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_plans.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

import asyncio  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select, update  # noqa: E402

from core.plans import (  # noqa: E402
    BILLED_FEATURES,
    ENTITLEMENTS,
    Plan,
    entitlements_for,
    month_start,
)
from db.session import SessionLocal  # noqa: E402
from main import app  # noqa: E402
from models.ai_interaction import AIInteraction  # noqa: E402
from models.user import User  # noqa: E402

PASSWORD = "StrongPass123"
ESSAY = "Urbanisation has reshaped how populations live and work worldwide. " * 6


def check_plan_parsing() -> None:
    assert Plan.parse("free") is Plan.FREE
    assert Plan.parse("  PLUS ") is Plan.PLUS

    # Fails to the LEAST generous plan. A typo in a plan name must not hand
    # someone unlimited AI; the worst case this way is a support message.
    assert Plan.parse("plsu") is Plan.FREE
    assert Plan.parse(None) is Plan.FREE
    assert Plan.parse("") is Plan.FREE


def check_entitlements_are_ordered() -> None:
    free = ENTITLEMENTS[Plan.FREE]
    plus = ENTITLEMENTS[Plan.PLUS]
    unlimited = ENTITLEMENTS[Plan.UNLIMITED]

    assert free.monthly_ai_attempts is not None
    assert plus.monthly_ai_attempts is not None
    assert plus.monthly_ai_attempts > free.monthly_ai_attempts
    assert unlimited.monthly_ai_attempts is None

    # A free tier that runs out on day two is a trial, not a free tier, and
    # people uninstall rather than upgrade.
    assert free.monthly_ai_attempts >= 20

    assert not free.spoken_interview
    assert plus.spoken_interview and unlimited.spoken_interview


def check_only_ai_features_are_billed() -> None:
    # Reading and listening are graded against an answer key: no model, no
    # money, so capping them would restrict practice for no reason.
    assert "reading" not in BILLED_FEATURES
    assert "listening" not in BILLED_FEATURES
    assert "writing" in BILLED_FEATURES and "speaking" in BILLED_FEATURES


async def _set_plan(email: str, plan: str) -> str:
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == email))
        assert user is not None
        await session.execute(
            update(User).where(User.id == user.id).values(plan=plan)
        )
        await session.commit()
        return user.id


async def _burn_allowance(user_id: str, count: int) -> None:
    """Write usage rows directly rather than making real scoring calls."""
    now = datetime.now(tz=timezone.utc)
    async with SessionLocal() as session:
        session.add_all(
            [
                AIInteraction(
                    user_id=user_id,
                    feature="writing",
                    provider="mock",
                    model="mock-heuristic",
                    total_tokens=100,
                    cost_usd=0.01,
                    status="ok",
                    created_at=now,
                )
                for _ in range(count)
            ]
        )
        # A failed call must not count against the allowance: charging someone
        # for a scoring attempt that errored is charging them for our outage.
        session.add(
            AIInteraction(
                user_id=user_id,
                feature="writing",
                provider="mock",
                model="mock-heuristic",
                status="failed",
                created_at=now,
            )
        )
        # Nor must last month's usage. The allowance is per calendar month.
        session.add(
            AIInteraction(
                user_id=user_id,
                feature="writing",
                provider="mock",
                model="mock-heuristic",
                status="ok",
                created_at=month_start(now) - timedelta(days=2),
            )
        )
        await session.commit()


def _auth(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/v1/auth/register",
        json={"fullName": "Plan Learner", "email": email, "password": PASSWORD},
    )
    token = client.post(
        "/v1/auth/login", json={"email": email, "password": PASSWORD}
    ).json()["tokens"]["accessToken"]
    h = {"Authorization": f"Bearer {token}"}
    client.post(
        "/v1/onboarding",
        headers=h,
        json={
            "examType": "academic",
            "selfLevel": "intermediate",
            "targetBand": 7.0,
            "examDate": None,
            "dailyMinutes": 30,
            "consentVoice": True,
            "consentAi": True,
        },
    )
    return h


def run() -> None:
    check_plan_parsing()
    check_entitlements_are_ordered()
    check_only_ai_features_are_billed()

    free_limit = entitlements_for("free").monthly_ai_attempts
    assert free_limit is not None

    with TestClient(app) as client:
        # ---------- A new learner is on free and can practise ----------
        h = _auth(client, "planned@example.com")
        usage = client.get("/v1/me/plan", headers=h)
        assert usage.status_code == 200, usage.text
        assert usage.json()["plan"] == "free"
        assert usage.json()["used"] == 0
        assert usage.json()["remaining"] == free_limit

        assert (
            client.post(
                "/v1/writing/attempts",
                headers=h,
                json={"essayText": ESSAY, "taskType": 2},
            ).status_code
            == 201
        )

        # ---------- At the limit ----------
        user_id = asyncio.run(_set_plan("planned@example.com", "free"))
        asyncio.run(_burn_allowance(user_id, free_limit))

        after = client.get("/v1/me/plan", headers=h).json()
        # Failed and last-month rows are excluded, so the count is exactly the
        # successful billed calls this month.
        assert after["used"] >= free_limit, after
        assert after["remaining"] == 0, after

        blocked = client.post(
            "/v1/writing/attempts",
            headers=h,
            json={"essayText": ESSAY, "taskType": 2},
        )
        assert blocked.status_code == 402, blocked.text
        assert blocked.json()["code"] == "plan_limit_reached"
        body = blocked.json()["title"] + blocked.text
        # The message says when it resets and what still works. "Limit reached"
        # alone leaves someone with no idea whether to wait or to pay.
        assert "resets" in body and "Reading" in body

        # ---------- What must still work at the limit ----------
        # Their own past work, which they have already paid for in effort.
        assert client.get("/v1/writing/history", headers=h).status_code == 200
        assert client.get("/v1/analytics/progress", headers=h).status_code == 200
        assert client.get("/v1/me/weaknesses", headers=h).status_code == 200

        # And the modules that cost nothing to grade.
        assert client.get("/v1/reading/passages", headers=h).status_code == 200
        assert client.get("/v1/listening/clips", headers=h).status_code == 200

        # ---------- Feature gating ----------
        interview = client.post("/v1/interview/sessions", headers=h)
        assert interview.status_code == 402, interview.text
        assert interview.json()["code"] in (
            "feature_not_in_plan",
            "plan_limit_reached",
        )

        # ---------- Upgrading restores access immediately ----------
        asyncio.run(_set_plan("planned@example.com", "unlimited"))
        upgraded = client.get("/v1/me/plan", headers=h).json()
        assert upgraded["plan"] == "unlimited"
        # Unlimited reports null rather than a huge number, so a client can
        # render "unlimited" instead of "9999 remaining".
        assert upgraded["limit"] is None
        assert upgraded["remaining"] is None

        assert (
            client.post(
                "/v1/writing/attempts",
                headers=h,
                json={"essayText": ESSAY, "taskType": 2},
            ).status_code
            == 201
        )
        assert client.post("/v1/interview/sessions", headers=h).status_code == 201

        # ---------- Access ----------
        assert client.get("/v1/me/plan").status_code in (401, 403)

    print("PLANS SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
