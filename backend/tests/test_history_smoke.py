"""Smoke test: paginated attempt history endpoints (cursor pagination)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_history.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

ESSAY = "Technology shapes the modern world in many important ways. " * 6


def run() -> None:
    with TestClient(app) as client:
        client.post(
            "/v1/auth/register",
            json={
                "fullName": "History User",
                "email": "history@example.com",
                "password": "StrongPass123",
            },
        )
        login = client.post(
            "/v1/auth/login",
            json={"email": "history@example.com", "password": "StrongPass123"},
        ).json()
        h = {"Authorization": f"Bearer {login['tokens']['accessToken']}"}

        # Create 3 writing attempts
        created = []
        for _ in range(3):
            r = client.post(
                "/v1/writing/attempts", headers=h, json={"essayText": ESSAY, "taskType": 2}
            )
            assert r.status_code == 201, r.text
            created.append(r.json()["attemptId"])

        # Page 1: limit 2 -> 2 items + a nextCursor
        r = client.get("/v1/writing/history?limit=2", headers=h)
        assert r.status_code == 200, r.text
        page1 = r.json()
        assert len(page1["items"]) == 2, page1
        assert page1["nextCursor"] is not None
        # Newest first
        for item in page1["items"]:
            assert item["overallBand"] is not None
            assert "createdAt" in item

        # Page 2: use cursor -> remaining 1 item, no further cursor
        r = client.get(
            f"/v1/writing/history?limit=2&cursor={page1['nextCursor']}", headers=h
        )
        assert r.status_code == 200, r.text
        page2 = r.json()
        assert len(page2["items"]) == 1, page2
        assert page2["nextCursor"] is None

        # No overlap between pages
        ids1 = {i["attemptId"] for i in page1["items"]}
        ids2 = {i["attemptId"] for i in page2["items"]}
        assert ids1.isdisjoint(ids2)
        assert ids1 | ids2 == set(created)

        # Other module histories respond (empty is fine)
        for module in ("speaking", "reading", "listening"):
            r = client.get(f"/v1/{module}/history", headers=h)
            assert r.status_code == 200, r.text
            assert r.json()["items"] == []

    print("HISTORY SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
