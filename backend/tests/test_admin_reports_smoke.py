"""Smoke test: platform reports.

The retention denominator is the assertion that matters. Counting a learner who
registered yesterday as churned for a 30-day window drags every cohort down and
makes retention look worse the faster the platform grows -- which is the exact
opposite of the truth, and the most common way this metric is got wrong.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_admin_reports.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from fastapi.testclient import TestClient  # noqa: E402

from core.config import get_settings  # noqa: E402
from db.session import SessionLocal  # noqa: E402
from main import app  # noqa: E402
from models.attempt import WritingAttempt  # noqa: E402
from models.user import User  # noqa: E402

PASSWORD = "StrongPass123"
ESSAY = "Urbanisation has reshaped how populations live and work. " * 6


async def _seed_history() -> None:
    """Two learners with deliberately different histories.

    One registered 40 days ago and came back on day 10; one registered
    yesterday and has done nothing. The second must not count against the
    30-day retention figure -- they have not had 30 days.
    """
    now = datetime.now(tz=timezone.utc)
    async with SessionLocal() as session:
        veteran = User(
            full_name="Veteran Learner",
            email="veteran@example.com",
            password_hash="x",
            created_at=now - timedelta(days=40),
        )
        newcomer = User(
            full_name="New Learner",
            email="newcomer@example.com",
            password_hash="x",
            created_at=now - timedelta(days=1),
        )
        session.add_all([veteran, newcomer])
        await session.flush()

        session.add_all(
            [
                WritingAttempt(
                    user_id=veteran.id,
                    task_type=2,
                    essay_text=ESSAY,
                    word_count=60,
                    overall_band=6.5,
                    created_at=now - timedelta(days=40),
                ),
                WritingAttempt(
                    user_id=veteran.id,
                    task_type=2,
                    essay_text=ESSAY,
                    word_count=60,
                    overall_band=7.5,
                    created_at=now - timedelta(days=30),
                ),
            ]
        )
        await session.commit()


def _admin(client: TestClient) -> dict[str, str]:
    settings = get_settings()
    token = client.post(
        "/v1/auth/login",
        json={
            "email": settings.seed_admin_email,
            "password": settings.seed_admin_password,
        },
    ).json()["tokens"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def run() -> None:
    import asyncio

    with TestClient(app) as client:
        asyncio.run(_seed_history())

        h = _admin(client)
        r = client.get("/v1/admin/reports", headers=h, params={"days": 30})
        assert r.status_code == 200, r.text
        data = r.json()

        # ---------- Daily ----------
        assert data["windowDays"] == 30
        daily = data["daily"]
        # Every day, including empty ones. Omitting quiet days compresses the
        # axis and makes a gap look like continuous activity.
        assert len(daily) == 30, len(daily)
        days = [point["day"] for point in daily]
        assert days == sorted(days), "days out of order"
        assert len(set(days)) == 30, "duplicate days"
        for point in daily:
            for key in ("newUsers", "activeLearners", "attempts", "aiCostUsd"):
                assert point[key] >= 0, point

        # ---------- Bands ----------
        bands = data["bands"]
        assert [b["label"] for b in bands] == [
            "below 5.0",
            "5.0 - 5.5",
            "6.0 - 6.5",
            "7.0 - 7.5",
            "8.0+",
        ]
        scored = sum(b["count"] for b in bands)
        assert scored >= 2, bands
        # Shares must add up. A distribution that does not sum to 100 is a
        # bucketing bug, and on a chart it looks like a rounding artefact.
        assert abs(sum(b["sharePct"] for b in bands) - 100.0) < 0.5, bands
        # The two seeded bands fall in different buckets, so neither is empty.
        assert next(b for b in bands if b["label"] == "6.0 - 6.5")["count"] >= 1
        assert next(b for b in bands if b["label"] == "7.0 - 7.5")["count"] >= 1

        # ---------- Retention ----------
        retention = {p["dayOffset"]: p for p in data["retention"]}
        assert set(retention) == {1, 3, 7, 14, 30}

        for point in retention.values():
            assert point["returned"] <= point["eligible"], point
            assert 0 <= point["ratePct"] <= 100, point

        # The learner who registered yesterday is eligible for day 1 and not
        # for day 30. Counting them as churned for a month they have not lived
        # through is what makes retention look worse the faster you grow.
        assert retention[30]["eligible"] < retention[1]["eligible"], retention

        # The veteran returned on day 10, so they count at 7 and not at 14.
        assert retention[7]["returned"] >= 1, retention
        assert retention[14]["returned"] == 0, retention

        assert data["generatedAt"]

        # ---------- Access ----------
        client.post(
            "/v1/auth/register",
            json={
                "fullName": "Nosy Learner",
                "email": "nosy@example.com",
                "password": PASSWORD,
            },
        )
        learner = {
            "Authorization": "Bearer "
            + client.post(
                "/v1/auth/login",
                json={"email": "nosy@example.com", "password": PASSWORD},
            ).json()["tokens"]["accessToken"]
        }
        assert client.get("/v1/admin/reports", headers=learner).status_code == 403
        assert client.get("/v1/admin/reports").status_code in (401, 403)

        # ---------- Window bounds ----------
        # Clamped rather than rejected: an out-of-range window is a caller
        # mistake, not a reason to show nothing.
        assert (
            client.get(
                "/v1/admin/reports", headers=h, params={"days": 0}
            ).json()["windowDays"]
            == 1
        )
        assert (
            client.get(
                "/v1/admin/reports", headers=h, params={"days": 100_000}
            ).json()["windowDays"]
            == 365
        )

    print("ADMIN REPORTS SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
