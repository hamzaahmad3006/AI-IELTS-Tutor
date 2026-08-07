"""Smoke test: weakness memory (record, recurrence, priority, decay)."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_weakness.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from controllers.weakness_controller import WeaknessService  # noqa: E402
from db.session import SessionLocal  # noqa: E402
from main import app  # noqa: E402
from models.weakness import Weakness  # noqa: E402

# Short, weak essay -> several criteria fall below the weakness threshold.
WEAK_ESSAY = "Technology is good. It helps people. I like it very much every day."


def _grammar_item(items: list[dict]) -> dict | None:
    for it in items:
        if it["module"] == "writing" and it["tag"] == "grammatical_range":
            return it
    return None


def run() -> None:
    with TestClient(app) as client:
        client.post(
            "/v1/auth/register",
            json={"fullName": "Weak Learner", "email": "weak@example.com", "password": "StrongPass123"},
        )
        login = client.post(
            "/v1/auth/login",
            json={"email": "weak@example.com", "password": "StrongPass123"},
        ).json()
        h = {"Authorization": f"Bearer {login['tokens']['accessToken']}"}

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
        user_id = login["user"]["id"]

        # No weaknesses yet
        assert client.get("/v1/me/weaknesses", headers=h).json()["items"] == []

        # First weak writing attempt -> weaknesses recorded
        client.post("/v1/writing/attempts", headers=h, json={"essayText": WEAK_ESSAY, "taskType": 2})
        items = client.get("/v1/me/weaknesses", headers=h).json()["items"]
        g1 = _grammar_item(items)
        assert g1 is not None, items
        assert g1["occurrences"] == 1
        sev1 = g1["severity"]
        assert 0 < sev1 <= 1

        # Recurrence -> severity rises, occurrences increments
        client.post("/v1/writing/attempts", headers=h, json={"essayText": WEAK_ESSAY, "taskType": 2})
        g2 = _grammar_item(client.get("/v1/me/weaknesses", headers=h).json()["items"])
        assert g2["occurrences"] == 2
        assert g2["severity"] > sev1

        # Wrong reading answer -> a reading-module weakness is recorded
        passage = client.get("/v1/reading/passages", headers=h).json()
        qids = [q["id"] for q in passage["questions"]]
        client.post(
            "/v1/reading/attempts",
            headers=h,
            json={"passageId": passage["id"], "answers": {qids[0]: "WRONG", qids[1]: "true", qids[2]: "black"}},
        )
        items = client.get("/v1/me/weaknesses", headers=h).json()["items"]
        assert any(i["module"] == "reading" for i in items), items
        # Sorted by priority descending
        priorities = [i["priority"] for i in items]
        assert priorities == sorted(priorities, reverse=True)

    # --- Decay: age the weaknesses ~40 days and run the decay job ---
    async def _decay() -> int:
        async with SessionLocal() as session:
            rows = list(await session.scalars(select(Weakness).where(Weakness.user_id == user_id)))
            old = datetime.now(timezone.utc) - timedelta(days=40)
            for w in rows:
                w.last_seen_at = old
            await session.commit()
            updated = await WeaknessService.apply_decay(session, user_id)
            await session.commit()
            return updated

    updated = asyncio.run(_decay())
    assert updated > 0

    # After heavy decay, active list is empty but resolved items remain visible
    with TestClient(app) as client:
        login = client.post(
            "/v1/auth/login",
            json={"email": "weak@example.com", "password": "StrongPass123"},
        ).json()
        h = {"Authorization": f"Bearer {login['tokens']['accessToken']}"}
        active = client.get("/v1/me/weaknesses", headers=h).json()["items"]
        assert active == [], active
        resolved = client.get("/v1/me/weaknesses?includeResolved=true", headers=h).json()["items"]
        assert len(resolved) > 0
        assert all(i["resolved"] for i in resolved)

    print("WEAKNESS MEMORY SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
