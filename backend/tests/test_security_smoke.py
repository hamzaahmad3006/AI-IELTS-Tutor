"""Security suite: authorization, token handling, injection, rate limits.

Every other suite checks that the app does what it should for the person it was
built for. This one checks what it does for someone it was not: a second
learner reaching for the first one's data, a forged token, a payload carrying
SQL. Rate limiting lives in test_ratelimit_smoke.py instead: the limit is bound
to the route at import time, so it needs process-level setup that would trip
over the many logins this suite makes.

Written as assertions about behaviour rather than implementation, so it keeps
its value if the internals are rewritten.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_security.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from fastapi.testclient import TestClient  # noqa: E402
from jose import jwt  # noqa: E402

from core.config import get_settings  # noqa: E402
from main import app  # noqa: E402

PASSWORD = "StrongPass123"
ESSAY = "Urbanisation has reshaped how populations live and work worldwide. " * 6
TRANSCRIPT = "I would like to describe a place I visited last year in some detail."

#: Payloads that must be stored and echoed as inert text, never interpreted.
INJECTION_STRINGS = [
    "'; DROP TABLE users; --",
    "' OR '1'='1",
    "1; DELETE FROM writing_attempts WHERE 1=1; --",
    "<script>alert(1)</script>",
    "../../etc/passwd",
    "${jndi:ldap://example.invalid/a}",
    "\x00truncated",
]


def _register(client: TestClient, email: str, name: str) -> dict[str, str]:
    client.post(
        "/v1/auth/register",
        json={"fullName": name, "email": email, "password": PASSWORD},
    )
    login = client.post(
        "/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert login.status_code == 200, login.text
    return {
        "Authorization": f"Bearer {login.json()['tokens']['accessToken']}",
    }


def check_cross_user_access(client: TestClient) -> None:
    """One learner must not reach another's work, and must not learn it exists."""
    alice = _register(client, "alice@example.com", "Alice Owner")
    bob = _register(client, "bob@example.com", "Bob Stranger")

    for h in (alice, bob):
        client.post(
            "/v1/onboarding",
            headers=h,
            json={
                "examType": "academic",
                "selfLevel": "intermediate",
                "targetBand": 7.0,
                "examDate": None,
                "dailyMinutes": 30,
                "consentVoice": False,
                "consentAi": True,
            },
        )

    created: dict[str, str] = {}
    w = client.post(
        "/v1/writing/attempts", headers=alice, json={"essayText": ESSAY, "taskType": 2}
    )
    assert w.status_code == 201, w.text
    created["writing"] = w.json()["attemptId"]

    s = client.post(
        "/v1/speaking/attempts",
        headers=alice,
        json={"transcript": TRANSCRIPT, "part": 2},
    )
    assert s.status_code == 201, s.text
    created["speaking"] = s.json()["attemptId"]

    for module, attempt_id in created.items():
        mine = client.get(f"/v1/{module}/attempts/{attempt_id}", headers=alice)
        assert mine.status_code == 200, (module, mine.text)

        # 404, not 403: "this exists but is not yours" confirms the id is real,
        # which is all an attacker needs to enumerate other people's data.
        theirs = client.get(f"/v1/{module}/attempts/{attempt_id}", headers=bob)
        assert theirs.status_code == 404, (module, theirs.status_code, theirs.text)

        # And the refusal must not leak the row through the error body.
        body = theirs.text.lower()
        assert "essay" not in body and "transcript" not in body, module

        # An id that does not exist is indistinguishable from one that does but
        # belongs to someone else. If these differed, the difference *is* the leak.
        missing = client.get(
            f"/v1/{module}/attempts/00000000-0000-0000-0000-000000000000",
            headers=bob,
        )
        assert missing.status_code == theirs.status_code, module
        assert missing.json().get("code") == theirs.json().get("code"), module

    # Neither learner appears in the other's history.
    for module, attempt_id in created.items():
        hist = client.get(f"/v1/{module}/history", headers=bob)
        assert hist.status_code == 200, hist.text
        assert attempt_id not in hist.text, module


def check_unauthenticated_access(client: TestClient) -> None:
    """Protected routes reject anonymous callers, and say nothing else."""
    protected = [
        ("GET", "/v1/auth/me"),
        ("GET", "/v1/writing/history"),
        ("GET", "/v1/speaking/history"),
        ("GET", "/v1/me/weaknesses"),
        ("GET", "/v1/me/recommendations"),
        ("GET", "/v1/me/adaptive-difficulty"),
        ("GET", "/v1/analytics/progress"),
        ("GET", "/v1/analytics/overview"),
        ("GET", "/v1/profile"),
        ("GET", "/v1/admin/overview"),
        ("GET", "/v1/admin/users"),
        ("POST", "/v1/writing/attempts"),
        ("POST", "/v1/speaking/attempts"),
    ]
    for method, path in protected:
        r = client.request(method, path, json={} if method == "POST" else None)
        assert r.status_code in (401, 403), f"{method} {path} -> {r.status_code}"

    # A malformed Authorization header is rejected, not parsed hopefully.
    for header in ("", "Bearer", "Bearer ", "Basic abc", "Bearer not.a.token", "Bearertoken"):
        r = client.get("/v1/auth/me", headers={"Authorization": header})
        assert r.status_code in (401, 403), (header, r.status_code)

    # Public routes stay public: the check above must not be passing because
    # everything returns 401.
    assert client.get("/health").status_code == 200


def check_token_integrity(client: TestClient) -> None:
    """Tokens are trusted only as far as their signature, and no further."""
    settings = get_settings()
    alice = _register(client, "tokens@example.com", "Token Holder")
    raw = alice["Authorization"].split(" ", 1)[1]
    claims = jwt.get_unverified_claims(raw)

    # Tampered payload, original signature.
    header, payload, signature = raw.split(".")
    forged = f"{header}.{payload[:-4]}AAAA.{signature}"
    assert client.get("/v1/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401

    # Signed with the wrong key.
    wrong_key = jwt.encode(claims, "not-the-server-secret", algorithm=settings.jwt_alg)
    assert client.get("/v1/auth/me", headers={"Authorization": f"Bearer {wrong_key}"}).status_code == 401

    # Unsigned "alg: none" -- the classic bypass.
    try:
        none_token = jwt.encode(claims, "", algorithm="none")
    except Exception:
        none_token = None  # the library refuses to mint one, which is also fine
    if none_token:
        r = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {none_token}"})
        assert r.status_code == 401, "unsigned token accepted"

    # Expired, correctly signed.
    expired = jwt.encode(
        {**claims, "exp": 1_600_000_000, "iat": 1_599_999_000},
        settings.jwt_secret,
        algorithm=settings.jwt_alg,
    )
    assert client.get("/v1/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401

    # A refresh token is not an access token. Token type is checked, so a
    # long-lived credential cannot be replayed against the API surface.
    login = client.post(
        "/v1/auth/login", json={"email": "tokens@example.com", "password": PASSWORD}
    ).json()
    refresh_raw = login["tokens"]["refreshToken"]
    r = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {refresh_raw}"})
    assert r.status_code == 401, "refresh token accepted as access token"


def check_privilege_escalation(client: TestClient) -> None:
    """Role is a property of the account, not a claim the caller supplies."""
    settings = get_settings()
    learner = _register(client, "escalate@example.com", "Escalation Attempt")

    admin_routes = ["/v1/admin/overview", "/v1/admin/users", "/v1/admin/ai-usage"]
    for path in admin_routes:
        assert client.get(path, headers=learner).status_code == 403, path

    # A *validly signed* token claiming super_admin. This is the important one:
    # if role were read from the token instead of the row, this would succeed,
    # and anyone who ever obtained a signing key could mint themselves an admin.
    claims = jwt.get_unverified_claims(learner["Authorization"].split(" ", 1)[1])
    escalated = jwt.encode(
        {**claims, "role": "super_admin"}, settings.jwt_secret, algorithm=settings.jwt_alg
    )
    for path in admin_routes:
        r = client.get(path, headers={"Authorization": f"Bearer {escalated}"})
        assert r.status_code == 403, f"{path}: role was trusted from the token"

    # Registration must not let a caller choose their own role.
    client.post(
        "/v1/auth/register",
        json={
            "fullName": "Self Promoted",
            "email": "selfpromo@example.com",
            "password": PASSWORD,
            "role": "super_admin",
            "isActive": True,
        },
    )
    promoted = _register(client, "selfpromo@example.com", "Self Promoted")
    assert client.get("/v1/admin/overview", headers=promoted).status_code == 403

    me = client.get("/v1/auth/me", headers=promoted)
    assert me.status_code == 200
    assert me.json().get("role") not in ("admin", "super_admin"), me.text

    # Nor may a profile update smuggle one in.
    client.post(
        "/v1/onboarding",
        headers=promoted,
        json={
            "examType": "academic",
            "selfLevel": "beginner",
            "targetBand": 6.0,
            "examDate": None,
            "dailyMinutes": 20,
            "consentVoice": False,
            "consentAi": True,
        },
    )
    client.patch("/v1/profile", headers=promoted, json={"role": "admin", "targetBand": 6.5})
    assert client.get("/v1/admin/overview", headers=promoted).status_code == 403


def check_injection(client: TestClient) -> None:
    """Hostile strings are data. They are stored, returned, and never executed."""
    h = _register(client, "inject@example.com", "Injection Tester")
    client.post(
        "/v1/onboarding",
        headers=h,
        json={
            "examType": "academic",
            "selfLevel": "intermediate",
            "targetBand": 7.0,
            "examDate": None,
            "dailyMinutes": 30,
            "consentVoice": False,
            "consentAi": True,
        },
    )

    for payload in INJECTION_STRINGS:
        essay = f"{payload} {ESSAY}"
        r = client.post(
            "/v1/writing/attempts", headers=h, json={"essayText": essay, "taskType": 2}
        )
        assert r.status_code in (201, 400, 422), (payload, r.status_code, r.text)

        # Whatever happened, the tables are still there and still serving.
        assert client.get("/v1/writing/history", headers=h).status_code == 200, payload
        assert client.get("/v1/auth/me", headers=h).status_code == 200, payload

    # Injection through a path parameter reaches a parameterised query, not the
    # SQL text -- so it is a miss, not an error, and certainly not a wildcard.
    for payload in ("' OR '1'='1", "1 OR 1=1", "%"):
        r = client.get(f"/v1/writing/attempts/{payload}", headers=h)
        assert r.status_code in (404, 422), (payload, r.status_code)

    # Injection through a query parameter likewise.
    r = client.get("/v1/writing/history", headers=h, params={"limit": "1; DROP TABLE users"})
    assert r.status_code in (200, 422), r.text
    assert client.post(
        "/v1/auth/login", json={"email": "inject@example.com", "password": PASSWORD}
    ).status_code == 200, "users table gone"

    # A password is never echoed back, in any casing, on any auth response.
    for r in (
        client.get("/v1/auth/me", headers=h),
        client.post(
            "/v1/auth/login",
            json={"email": "inject@example.com", "password": PASSWORD},
        ),
    ):
        assert PASSWORD not in r.text
        assert "passwordHash" not in r.text and "password_hash" not in r.text

    # Login must not reveal which half of the pair was wrong: a distinguishable
    # response turns the login form into an account-existence oracle.
    unknown = client.post(
        "/v1/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}
    )
    wrong_pw = client.post(
        "/v1/auth/login", json={"email": "inject@example.com", "password": "WrongPass123"}
    )
    assert unknown.status_code == wrong_pw.status_code, (
        unknown.status_code,
        wrong_pw.status_code,
    )

    # Compare the whole body minus correlationId, which is per-request by
    # design. Comparing one hand-picked field is how this assertion passes
    # vacuously: an earlier version compared `detail`, which this API does not
    # emit, so it was asserting None == None and would have missed a real leak.
    def _shape(response: object) -> dict[str, object]:
        body = dict(response.json())  # type: ignore[attr-defined]
        body.pop("correlationId", None)
        return body

    assert _shape(unknown) == _shape(wrong_pw), (_shape(unknown), _shape(wrong_pw))
    assert "title" in _shape(unknown), "nothing meaningful was compared"


def run() -> None:
    with TestClient(app) as client:
        check_unauthenticated_access(client)
        check_cross_user_access(client)
        check_token_integrity(client)
        check_privilege_escalation(client)
        check_injection(client)

    print("SECURITY SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
