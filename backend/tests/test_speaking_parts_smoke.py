"""Smoke test: /speaking/questions sets for Part 1 and Part 3."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_speaking_parts.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from fastapi.testclient import TestClient  # noqa: E402

from controllers.speaking_questions import QUESTIONS_PER_SET  # noqa: E402
from main import app  # noqa: E402


def run() -> None:
    with TestClient(app) as client:
        client.post(
            "/v1/auth/register",
            json={
                "fullName": "Omar Haddad",
                "email": "parts@example.com",
                "password": "StrongPass123",
            },
        )
        login = client.post(
            "/v1/auth/login",
            json={"email": "parts@example.com", "password": "StrongPass123"},
        ).json()
        h = {"Authorization": f"Bearer {login['tokens']['accessToken']}"}

        assert client.get("/v1/speaking/questions?part=1").status_code in (401, 403)

        for part in (1, 3):
            r = client.get(f"/v1/speaking/questions?part={part}", headers=h)
            assert r.status_code == 200, r.text
            d = r.json()

            assert d["part"] == part
            assert d["topic"], d
            assert len(d["questions"]) == QUESTIONS_PER_SET[part], d["questions"]

            # A themed run must arrive in order; shuffled questions would read
            # as a jumble rather than a conversation.
            orders = [q["orderIndex"] for q in d["questions"]]
            assert orders == sorted(orders), orders
            assert all(q["question"].strip() for q in d["questions"])
            assert len({q["id"] for q in d["questions"]}) == len(d["questions"])

            # The two parts are answered differently, so the guidance must
            # differ rather than being generic filler.
            assert d["guidance"], d

        part1 = client.get("/v1/speaking/questions?part=1", headers=h).json()
        part3 = client.get("/v1/speaking/questions?part=3", headers=h).json()
        assert part1["guidance"] != part3["guidance"]

        # Part 2 is cue cards, not a question set, and says so rather than
        # quietly returning the wrong shape.
        r = client.get("/v1/speaking/questions?part=2", headers=h)
        assert r.status_code == 400, r.text

        # Out-of-range parts are rejected by validation.
        assert client.get("/v1/speaking/questions?part=9", headers=h).status_code == 422

        # An unavailable difficulty falls back within the same part, never
        # across parts.
        r = client.get(
            "/v1/speaking/questions?part=3&difficulty=easy", headers=h
        )
        assert r.status_code == 200, r.text
        assert r.json()["part"] == 3

    print("SPEAKING PARTS SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
