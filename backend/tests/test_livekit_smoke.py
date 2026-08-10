"""Smoke test: LiveKit access tokens.

A token is the entire authorisation story for a room -- the LiveKit server
validates the signature and asks nobody anything -- so the claims have to be
exactly right. Wrong grant field names produce a token that parses, signs, and
grants nothing, which is the kind of failure that only shows up as "the app
connects and then silently hears nothing".
"""

from __future__ import annotations

import os
import time
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_livekit.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)
from tests._plans import grant_plan  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402
from jose import JWTError, jwt  # noqa: E402

from core.config import get_settings  # noqa: E402
from core.livekit import (  # noqa: E402
    DEFAULT_TTL_SECONDS,
    VideoGrant,
    decode_for_tests,
    mint_access_token,
    room_name_for,
)
from main import app  # noqa: E402

KEY = "devkey"
SECRET = "secret-for-tests-only"
URL = "ws://localhost:7880"
PASSWORD = "StrongPass123"


def check_claims() -> None:
    # Real current time, not a pinned future one: a token whose nbf is in the
    # future is correctly refused as not-yet-valid, so pinning ahead tests the
    # library's clock check rather than our claims.
    now = int(time.time())
    minted = mint_access_token(
        api_key=KEY,
        api_secret=SECRET,
        url=URL,
        room="interview-abc",
        identity="user-123",
        name="Sara Ahmed",
        now=now,
    )

    claims = decode_for_tests(minted.token, SECRET)
    assert claims["iss"] == KEY
    assert claims["sub"] == "user-123"
    assert claims["nbf"] == now
    assert claims["exp"] == now + DEFAULT_TTL_SECONDS
    assert claims["name"] == "Sara Ahmed"

    # LiveKit's field names, verbatim. Renaming any of these to something more
    # Pythonic yields a token that signs cleanly and grants nothing -- which
    # surfaces as "connects, then hears silence", not as an error.
    grant = claims["video"]
    assert grant["room"] == "interview-abc"
    assert grant["roomJoin"] is True
    assert grant["canPublish"] is True
    assert grant["canSubscribe"] is True
    assert grant["canPublishData"] is True

    # A learner must not be able to create rooms or administer them: room
    # creation is creation for anybody, and rooms are named after session ids.
    assert grant["roomCreate"] is False
    assert grant["roomAdmin"] is False

    assert minted.url == URL and minted.room == "interview-abc"
    assert minted.expires_at == now + DEFAULT_TTL_SECONDS


def check_signature_and_expiry() -> None:
    minted = mint_access_token(
        api_key=KEY, api_secret=SECRET, url=URL, room="r", identity="u"
    )

    # Signed with the LiveKit secret, so the wrong key must not verify. If it
    # did, anyone holding our own JWT secret could mint room access.
    try:
        decode_for_tests(minted.token, "not-the-secret")
    except JWTError:
        pass
    else:  # pragma: no cover
        raise AssertionError("a token verified under the wrong secret")

    expired = mint_access_token(
        api_key=KEY,
        api_secret=SECRET,
        url=URL,
        room="r",
        identity="u",
        ttl_seconds=60,
        now=1_600_000_000,
    )
    try:
        decode_for_tests(expired.token, SECRET)
    except JWTError:
        pass
    else:  # pragma: no cover
        raise AssertionError("an expired token still verified")

    # The token itself carries no secret material: it is handed to a phone.
    payload = jwt.get_unverified_claims(minted.token)
    assert SECRET not in str(payload)


def check_rejections() -> None:
    base = {"api_key": KEY, "api_secret": SECRET, "url": URL, "room": "r"}
    bad = [
        ("no identity", {**base, "identity": ""}),
        ("no key", {**base, "api_key": "", "identity": "u"}),
        ("no secret", {**base, "api_secret": "", "identity": "u"}),
        ("zero ttl", {**base, "identity": "u", "ttl_seconds": 0}),
        ("negative ttl", {**base, "identity": "u", "ttl_seconds": -1}),
    ]
    for label, kwargs in bad:
        try:
            mint_access_token(**kwargs)  # type: ignore[arg-type]
        except ValueError:
            pass
        else:  # pragma: no cover
            raise AssertionError(f"{label} should have been rejected")


def check_room_naming() -> None:
    # Deterministic, so a reconnecting client rejoins the room it left rather
    # than creating a second one and talking to nobody.
    assert room_name_for("abc") == room_name_for("abc")
    assert room_name_for("abc") != room_name_for("abd")
    assert "abc" in room_name_for("abc")


def check_grant_scoping() -> None:
    """A token grants one room, not any room."""
    minted = mint_access_token(
        api_key=KEY,
        api_secret=SECRET,
        url=URL,
        room="interview-mine",
        identity="u",
        grant=VideoGrant(room="interview-mine"),
    )
    assert decode_for_tests(minted.token, SECRET)["video"]["room"] == "interview-mine"


def check_endpoint() -> None:
    settings = get_settings()
    with TestClient(app) as client:
        client.post(
            "/v1/auth/register",
            json={
                "fullName": "RTC Learner",
                "email": "rtc@example.com",
                "password": PASSWORD,
            },
        )
        h = {
            "Authorization": "Bearer "
            + client.post(
                "/v1/auth/login",
                json={"email": "rtc@example.com", "password": PASSWORD},
            ).json()["tokens"]["accessToken"]
        }
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
        grant_plan("rtc@example.com")
        session_id = client.post("/v1/interview/sessions", headers=h).json()["id"]

        # Unconfigured, the endpoint says so plainly instead of 500-ing. The
        # upload path still works, so this is a degraded feature, not an outage.
        if not settings.livekit_enabled:
            r = client.post(f"/v1/interview/sessions/{session_id}/rtc-token", headers=h)
            assert r.status_code == 503, r.text
            assert "docker compose" in r.text, "the fix was not explained"

        # Ownership is enforced before configuration is even considered, so an
        # unconfigured server cannot be used to probe which sessions exist.
        client.post(
            "/v1/auth/register",
            json={
                "fullName": "Other Learner",
                "email": "rtc-other@example.com",
                "password": PASSWORD,
            },
        )
        other = {
            "Authorization": "Bearer "
            + client.post(
                "/v1/auth/login",
                json={"email": "rtc-other@example.com", "password": PASSWORD},
            ).json()["tokens"]["accessToken"]
        }
        assert (
            client.post(
                f"/v1/interview/sessions/{session_id}/rtc-token", headers=other
            ).status_code
            == 404
        )

        assert (
            client.post(f"/v1/interview/sessions/{session_id}/rtc-token").status_code
            in (401, 403)
        )


def run() -> None:
    check_claims()
    check_signature_and_expiry()
    check_rejections()
    check_room_naming()
    check_grant_scoping()
    check_endpoint()

    print("LIVEKIT SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
