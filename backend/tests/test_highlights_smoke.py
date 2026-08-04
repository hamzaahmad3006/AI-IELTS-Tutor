"""Smoke test: transcript highlight spans + the resolver that guards them."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_highlights.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from fastapi.testclient import TestClient  # noqa: E402

from core.highlights import resolve_highlights  # noqa: E402
from main import app  # noqa: E402

TRANSCRIPT = (
    "I think technology is very useful for study. It help me to find "
    "information quickly and easy. But sometime I spend too much time on my "
    "phone instead of reading books."
)


def check_resolver() -> None:
    # Verbatim quote resolves to the exact span.
    found = resolve_highlights(
        TRANSCRIPT, [{"quote": "It help me to find", "tag": "grammar", "note": "n"}]
    )
    assert len(found) == 1
    assert TRANSCRIPT[found[0].start : found[0].end] == "It help me to find"

    # A paraphrase is dropped rather than highlighted somewhere plausible.
    # Highlighting words the learner never wrote tells them they made a
    # mistake they did not make.
    assert resolve_highlights(
        TRANSCRIPT,
        [{"quote": "It helps me to find", "tag": "grammar", "note": "n"}],
    ) == []

    # Whitespace differences are tolerated, since models re-wrap text.
    spaced = resolve_highlights(
        TRANSCRIPT,
        [{"quote": "It help me\n  to find", "tag": "grammar", "note": "n"}],
    )
    assert len(spaced) == 1, spaced
    assert spaced[0].quote == "It help me to find"

    # Overlapping spans collapse to one so the UI never nests highlights.
    overlapping = resolve_highlights(
        TRANSCRIPT,
        [
            {"quote": "It help me to find", "tag": "a", "note": "n"},
            {"quote": "help me to find information", "tag": "b", "note": "n"},
        ],
    )
    assert len(overlapping) == 1, overlapping

    # Results are ordered by position, whatever order the model reported them.
    ordered = resolve_highlights(
        TRANSCRIPT,
        [
            {"quote": "reading books", "tag": "a", "note": "n"},
            {"quote": "I think technology", "tag": "b", "note": "n"},
        ],
    )
    assert [h.quote for h in ordered] == ["I think technology", "reading books"]

    # Empty and missing quotes are ignored, not crashed on.
    assert resolve_highlights(TRANSCRIPT, [{"quote": "", "tag": "a", "note": ""}]) == []
    assert resolve_highlights(TRANSCRIPT, [{}]) == []


def run() -> None:
    check_resolver()

    with TestClient(app) as client:
        client.post(
            "/v1/auth/register",
            json={
                "fullName": "Lena Fischer",
                "email": "highlights@example.com",
                "password": "StrongPass123",
            },
        )
        login = client.post(
            "/v1/auth/login",
            json={"email": "highlights@example.com", "password": "StrongPass123"},
        ).json()
        h = {"Authorization": f"Bearer {login['tokens']['accessToken']}"}

        r = client.post(
            "/v1/speaking/attempts",
            headers=h,
            json={"transcript": TRANSCRIPT, "part": 1, "durationSec": 60},
        )
        assert r.status_code == 201, r.text
        d = r.json()

        # The transcript comes back so the client can render the highlights
        # against it rather than keeping its own copy.
        assert d["transcript"] == TRANSCRIPT
        assert d["issues"], d

        for issue in d["issues"]:
            assert 0 <= issue["start"] < issue["end"] <= len(TRANSCRIPT)
            # Every span must genuinely address the learner's own words.
            assert TRANSCRIPT[issue["start"] : issue["end"]] == issue["quote"]
            assert issue["tag"] and issue["note"]

        starts = [i["start"] for i in d["issues"]]
        assert starts == sorted(starts)

        # Highlights survive a re-fetch rather than being recomputed differently.
        again = client.get(
            f"/v1/speaking/attempts/{d['attemptId']}", headers=h
        ).json()
        assert again["issues"] == d["issues"]

        # Writing returns the learner's text alongside the improved version, so
        # a diff can be rendered without the client caching its own copy.
        w = client.post(
            "/v1/writing/attempts",
            headers=h,
            json={"essayText": "Technology is good for us. " * 20, "taskType": 2},
        ).json()
        assert w["essayText"].startswith("Technology is good"), w["essayText"][:40]
        assert w["improvedEssay"] is not None

    print("HIGHLIGHTS SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
