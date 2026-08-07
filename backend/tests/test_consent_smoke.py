"""Smoke test: consent is enforced, not just collected.

Consent was stored on the profile and then never read. A checkbox that changes
no behaviour is not consent, it is decoration -- and it is worse than no
checkbox, because it tells the learner a decision was respected when it was not.

These tests exist to make that impossible to regress silently: every one of them
would pass again if the guards were deleted, so each asserts a *refusal*.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_consent.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

PASSWORD = "StrongPass123"
ESSAY = "Urbanisation has reshaped how populations live and work worldwide. " * 6
TRANSCRIPT = "I would like to describe a place I visited last year in some detail."


def _register(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/v1/auth/register",
        json={"fullName": "Consent Learner", "email": email, "password": PASSWORD},
    )
    token = client.post(
        "/v1/auth/login", json={"email": email, "password": PASSWORD}
    ).json()["tokens"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def _onboard(client: TestClient, h: dict, *, ai: bool, voice: bool) -> None:
    r = client.post(
        "/v1/onboarding",
        headers=h,
        json={
            "examType": "academic",
            "selfLevel": "intermediate",
            "targetBand": 7.0,
            "examDate": None,
            "dailyMinutes": 30,
            "consentVoice": voice,
            "consentAi": ai,
        },
    )
    assert r.status_code in (200, 201), r.text


def check_never_asked_is_not_agreed() -> None:
    """An account that skipped onboarding has consented to nothing.

    The tempting alternative -- treat "never asked" as "agreed" -- makes the
    whole mechanism a formality, because skipping one screen buys the
    permissive path forever.
    """
    with TestClient(app) as client:
        h = _register(client, "never-asked@example.com")

        r = client.post(
            "/v1/writing/attempts", headers=h, json={"essayText": ESSAY, "taskType": 2}
        )
        assert r.status_code == 403, r.text
        assert r.json()["code"] == "consent_required", r.json()

        # 403, not 401: the caller is authenticated and known. Nothing is wrong
        # with their credentials; they simply have not permitted this.
        assert r.json()["status"] == 403


def check_ai_consent_refused() -> None:
    with TestClient(app) as client:
        h = _register(client, "no-ai@example.com")
        _onboard(client, h, ai=False, voice=True)

        for path, payload in (
            ("/v1/writing/attempts", {"essayText": ESSAY, "taskType": 2}),
            ("/v1/speaking/attempts", {"transcript": TRANSCRIPT, "part": 2}),
        ):
            r = client.post(path, headers=h, json=payload)
            assert r.status_code == 403, (path, r.text)
            assert r.json()["code"] == "consent_required"
            # The message says how to fix it. "Forbidden" alone leaves the
            # learner with a dead screen and no idea why.
            assert "profile" in r.json()["title"].lower(), r.json()

        # Nothing was written. Recording an attempt we then refused to score
        # would leave a permanently unscored row in their history.
        history = client.get("/v1/writing/history", headers=h)
        assert history.status_code == 200
        assert history.json()["items"] == [], history.json()


def check_voice_consent_is_separate() -> None:
    """Agreeing to AI scoring is not agreeing to be recorded.

    Someone can be perfectly happy having an essay marked and unwilling to have
    their voice captured, and one flag for both denies them that.
    """
    with TestClient(app) as client:
        h = _register(client, "no-voice@example.com")
        _onboard(client, h, ai=True, voice=False)

        # AI scoring works: they agreed to that.
        r = client.post(
            "/v1/writing/attempts", headers=h, json={"essayText": ESSAY, "taskType": 2}
        )
        assert r.status_code == 201, r.text

        # Recording does not.
        session_id = client.post("/v1/interview/sessions", headers=h).json()["id"]
        upload = client.post(
            f"/v1/interview/sessions/{session_id}/answer-audio",
            headers=h,
            files={"audio": ("a.wav", b"RIFF" + bytes(512), "audio/wav")},
        )
        assert upload.status_code == 403, upload.text
        assert upload.json()["code"] == "consent_required"

        # ...but they can still take the exam by typing, so declining voice
        # costs one input method rather than the whole feature.
        typed = client.post(
            f"/v1/interview/sessions/{session_id}/answer",
            headers=h,
            json={"text": "I would rather type this.", "source": "typed"},
        )
        assert typed.status_code == 200, typed.text


def check_consent_granted_allows_everything() -> None:
    with TestClient(app) as client:
        h = _register(client, "full-consent@example.com")
        _onboard(client, h, ai=True, voice=True)

        assert (
            client.post(
                "/v1/writing/attempts",
                headers=h,
                json={"essayText": ESSAY, "taskType": 2},
            ).status_code
            == 201
        )
        session_id = client.post("/v1/interview/sessions", headers=h).json()["id"]
        assert (
            client.post(
                f"/v1/interview/sessions/{session_id}/answer-audio",
                headers=h,
                files={"audio": ("a.wav", b"RIFF" + bytes(512), "audio/wav")},
            ).status_code
            == 200
        )


def check_revocation_takes_effect_immediately() -> None:
    """Turning consent off applies to the next request, not the next login.

    Checked at the point of use rather than cached at sign-in, because a
    learner who withdraws consent and then watches the app keep scoring their
    work has not withdrawn anything.
    """
    with TestClient(app) as client:
        h = _register(client, "revoker@example.com")
        _onboard(client, h, ai=True, voice=True)

        assert (
            client.post(
                "/v1/writing/attempts",
                headers=h,
                json={"essayText": ESSAY, "taskType": 2},
            ).status_code
            == 201
        )

        # Same token, consent withdrawn.
        patched = client.patch("/v1/profile", headers=h, json={"consentAi": False})
        assert patched.status_code == 200, patched.text

        r = client.post(
            "/v1/writing/attempts", headers=h, json={"essayText": ESSAY, "taskType": 2}
        )
        assert r.status_code == 403, r.text
        assert r.json()["code"] == "consent_required"


def run() -> None:
    check_never_asked_is_not_agreed()
    check_ai_consent_refused()
    check_voice_consent_is_separate()
    check_consent_granted_allows_everything()
    check_revocation_takes_effect_immediately()

    print("CONSENT SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
