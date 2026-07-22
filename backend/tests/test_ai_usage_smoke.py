"""Smoke test: AI usage logging + admin monitoring endpoint + RBAC."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_aiusage.db")

from fastapi.testclient import TestClient  # noqa: E402

from core.config import get_settings  # noqa: E402
from main import app  # noqa: E402


def run() -> None:
    settings = get_settings()
    with TestClient(app) as client:
        # Learner registers and generates two AI scoring calls
        client.post(
            "/v1/auth/register",
            json={
                "fullName": "Usage Learner",
                "email": "usage@example.com",
                "password": "StrongPass123",
            },
        )
        learner = client.post(
            "/v1/auth/login",
            json={"email": "usage@example.com", "password": "StrongPass123"},
        ).json()
        lh = {"Authorization": f"Bearer {learner['tokens']['accessToken']}"}

        client.post(
            "/v1/writing/attempts",
            headers=lh,
            json={"essayText": "This is a reasonably detailed essay about technology and society. " * 6, "taskType": 2},
        )
        client.post(
            "/v1/speaking/attempts",
            headers=lh,
            json={"transcript": "I recently visited a beautiful coastal town and enjoyed the scenery. " * 4, "part": 2},
        )

        # Learner must NOT access the admin endpoint
        r = client.get("/v1/admin/ai-usage", headers=lh)
        assert r.status_code == 403, r.text

        # Seeded admin logs in
        admin = client.post(
            "/v1/auth/login",
            json={
                "email": settings.seed_admin_email,
                "password": settings.seed_admin_password,
            },
        ).json()
        ah = {"Authorization": f"Bearer {admin['tokens']['accessToken']}"}

        # Aggregate usage
        r = client.get("/v1/admin/ai-usage", headers=ah)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["totals"]["calls"] >= 2, data
        assert data["totals"]["totalTokens"] > 0
        assert data["totals"]["errorRate"] == 0.0
        assert len(data["byModel"]) >= 1

        # Filter by feature
        r = client.get("/v1/admin/ai-usage?feature=writing", headers=ah)
        assert r.status_code == 200, r.text
        assert r.json()["totals"]["calls"] >= 1

    print("AI USAGE + ADMIN SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
