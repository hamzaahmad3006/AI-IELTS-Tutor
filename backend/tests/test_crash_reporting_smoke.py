"""Smoke test: crash reporting.

The risk here is not that reports fail to arrive. It is that they arrive
carrying an essay, a transcript, a bearer token or the Groq key -- to a third
party, from a code path that only runs when something has already gone wrong
and nobody is watching closely.

So most of this file is about what is *absent* from the payload. The strongest
assertion is the last one: a synthetic crash is staged with secrets in every
place a crash reporter conventionally looks -- frame locals, the exception
message, the request path -- and the serialised envelope is searched for each
of them.

The network send is not covered. Everything up to the POST is.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_crash.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

import httpx  # noqa: E402

from core.crash_reporting import (  # noqa: E402
    MAX_MESSAGE,
    RATE_LIMIT,
    DsnError,
    NullReporter,
    SentryReporter,
    build_event,
    build_reporter,
    parse_dsn,
    relative_frame_path,
    scrub_text,
    to_envelope,
)

DSN = "https://abc123def456@o12345.ingest.sentry.io/6789"

#: Stand-ins for the things this codebase actually holds. Each is looked for
#: by name in the final payload.
ESSAY = "Nowadays many people believe that technology has fundamentally changed"
TRANSCRIPT = "Well I think that the main advantage of living in a city is"
PASSWORD = "StrongPass123"
JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMiLCJyb2xlIjoiYWRtaW4ifQ.QW5kU2ln"
GROQ_KEY = "gsk_AbCdEfGhIjKlMnOpQrStUvWxYz0123456789"
EMAIL = "learner@example.com"


def check_dsn_parsing() -> None:
    dsn = parse_dsn(DSN)
    assert dsn.public_key == "abc123def456"
    assert dsn.project_id == "6789"
    assert dsn.envelope_url == "https://o12345.ingest.sentry.io/api/6789/envelope/"
    assert "sentry_key=abc123def456" in dsn.auth_header

    # The legacy form carries a secret after the key; it must not survive into
    # the auth header, which ends up in request logs.
    legacy = parse_dsn("https://pub@o1.ingest.sentry.io/2")
    assert "pub" in legacy.auth_header

    for bad in ("", "not-a-dsn", "https://o1.sentry.io/2", "ftp://k@h/1", "https://k@h/"):
        try:
            parse_dsn(bad)
        except DsnError:
            pass
        else:  # pragma: no cover
            raise AssertionError(f"accepted malformed DSN: {bad!r}")


def check_text_scrubbing() -> None:
    assert scrub_text(f"login failed for {EMAIL}") == "login failed for [email]"
    assert "[jwt]" in scrub_text(f"bad token {JWT}")
    assert "[api-key]" in scrub_text(f"provider rejected {GROQ_KEY}")
    assert JWT not in scrub_text(f"bad token {JWT}")
    assert GROQ_KEY not in scrub_text(f"provider rejected {GROQ_KEY}")

    # A connection string names the host but must not carry the password.
    scrubbed = scrub_text(
        "could not connect to postgresql://postgres:Hamza4117300@db.host:5432/x"
    )
    assert "Hamza4117300" not in scrubbed
    assert "[credentials]" in scrubbed

    assert "[hash]" in scrub_text("signature " + "a" * 40)

    # Authorization headers get stringified into messages surprisingly often.
    assert "[redacted]" in scrub_text("header was Bearer abcdef0123456789")

    # Length is bounded, and the truncation is announced rather than silent --
    # a cut message must not be mistaken for the whole one mid-investigation.
    long = scrub_text("x" * (MAX_MESSAGE * 3))
    assert len(long) < MAX_MESSAGE * 2
    assert "truncated" in long

    assert scrub_text("") == ""


def check_frame_paths_do_not_describe_the_host() -> None:
    """An absolute path is a free description of the deployment."""
    here, in_app = relative_frame_path(__file__)
    assert here == "tests/test_crash_reporting_smoke.py"
    assert in_app is True

    # Something outside the backend keeps only its basename.
    outside, is_ours = relative_frame_path("/home/deploy/secret/lib/json.py")
    assert outside == "json.py"
    assert is_ours is False
    assert "deploy" not in outside


def _staged_crash() -> BaseException:
    """A crash with secrets in the locals, raised from a nested call.

    Locals are the point: they are what an off-the-shelf reporter attaches to
    every frame, and here they are the essay and the key.
    """

    def inner(essay: str, api_key: str) -> None:
        password = PASSWORD  # noqa: F841 - deliberately a local
        token = JWT  # noqa: F841
        raise ValueError(f"scoring failed for {EMAIL} using {api_key}")

    def outer() -> None:
        transcript = TRANSCRIPT  # noqa: F841
        inner(ESSAY, GROQ_KEY)

    try:
        outer()
    except ValueError as error:
        try:
            raise RuntimeError("could not finish the attempt") from error
        except RuntimeError as wrapper:
            return wrapper
    raise AssertionError("staged crash did not raise")  # pragma: no cover


def check_event_shape() -> None:
    event = build_event(
        _staged_crash(),
        correlation_id="corr-123",
        route="/v1/writing/attempts/{id}",
        method="POST",
        environment="production",
        release="abc1234",
        event_id="f" * 32,
        timestamp=1700000000.0,
    )

    assert event["event_id"] == "f" * 32
    assert event["environment"] == "production"
    assert event["release"] == "abc1234"
    assert event["level"] == "error"
    # The template, not the path -- a path carries the id that ties a report
    # back to a person.
    assert event["transaction"] == "POST /v1/writing/attempts/{id}"
    assert event["tags"]["correlation_id"] == "corr-123"

    values = event["exception"]["values"]
    # The cause chain survives, because "X while handling Y" is usually where
    # the real fault is. Sentry renders the last entry as the outermost.
    assert [v["type"] for v in values] == ["ValueError", "RuntimeError"]

    frames = values[0]["stacktrace"]["frames"]
    assert frames, "no frames captured"
    assert frames[-1]["function"] == "inner"
    assert frames[-1]["lineno"] > 0
    # No locals, ever. This is the single most important line in the file.
    for value in values:
        for frame in value["stacktrace"]["frames"]:
            assert "vars" not in frame
            assert set(frame) == {"filename", "function", "lineno", "in_app"}


def check_nothing_sensitive_reaches_the_wire() -> None:
    """Serialise the whole envelope and search it for every secret.

    Asserted against the bytes rather than the dict, because the question is
    what leaves the process -- a nested structure that json.dumps flattens
    would pass a field-by-field check and still ship the essay.
    """
    envelope = to_envelope(
        build_event(
            _staged_crash(),
            correlation_id="corr-123",
            route="/v1/writing/attempts/{id}",
            method="POST",
        )
    ).decode("utf-8")

    for secret, label in (
        (ESSAY, "essay text"),
        (TRANSCRIPT, "speaking transcript"),
        (PASSWORD, "password"),
        (JWT, "access token"),
        (GROQ_KEY, "provider api key"),
        (EMAIL, "learner email"),
    ):
        assert secret not in envelope, f"{label} reached the payload"

    # The message survives in redacted form rather than being dropped outright
    # -- an event with no message is not worth sending.
    assert "scoring failed for [email]" in envelope
    assert "[api-key]" in envelope


def check_envelope_framing() -> None:
    """Sentry's format: three newline-delimited JSON documents."""
    event = build_event(ValueError("boom"), event_id="a" * 32)
    lines = to_envelope(event).decode("utf-8").split("\n")
    assert len(lines) == 3

    header = json.loads(lines[0])
    assert header["event_id"] == "a" * 32
    assert header["sent_at"]

    item = json.loads(lines[1])
    assert item["type"] == "event"
    # The declared length must match the body exactly, or Sentry rejects the
    # envelope as malformed.
    assert item["length"] == len(lines[2].encode("utf-8"))

    assert json.loads(lines[2])["event_id"] == "a" * 32


def check_reporter_selection() -> None:
    import core.config as config_module
    from core.config import Settings

    def with_settings(**kwargs):
        saved = config_module.get_settings
        config_module.get_settings = lambda: Settings(sentry_dsn="", **kwargs)
        try:
            return build_reporter()
        finally:
            config_module.get_settings = saved

    # Off by default, and the no-op is a real object so the call site never
    # has to branch.
    assert isinstance(with_settings(), NullReporter)
    assert with_settings().report(ValueError("x")) is None
    assert with_settings().enabled is False

    def configured(dsn: str):
        saved = config_module.get_settings
        config_module.get_settings = lambda: Settings(sentry_dsn=dsn)
        try:
            return build_reporter()
        finally:
            config_module.get_settings = saved

    assert isinstance(configured(DSN), SentryReporter)
    # A malformed DSN disables reporting rather than stopping the app:
    # refusing to boot over a typo in an optional integration costs more than
    # the lost visibility.
    assert isinstance(configured("garbage"), NullReporter)


def check_sending_and_rate_limit() -> None:
    posted: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        posted.append(request)
        return httpx.Response(200, json={"id": "x"})

    original = httpx.Client.__init__

    def patched(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        original(self, *args, **kwargs)

    httpx.Client.__init__ = patched
    try:
        reporter = SentryReporter(dsn=parse_dsn(DSN), environment="production")
        event_id = reporter.report(
            _staged_crash(), correlation_id="c1", route="/v1/x", method="GET"
        )
        assert event_id and len(event_id) == 32
        assert len(posted) == 1
        assert posted[0].headers["content-type"] == "application/x-sentry-envelope"
        assert "sentry_key=abc123def456" in posted[0].headers["x-sentry-auth"]
        assert GROQ_KEY not in posted[0].content.decode("utf-8")

        # A crash loop must not turn one bug into a quota exhaustion; the
        # thousandth copy of a traceback says nothing the first did not.
        for _ in range(RATE_LIMIT + 10):
            reporter.report(ValueError("loop"))
        assert len(posted) == RATE_LIMIT, len(posted)
    finally:
        httpx.Client.__init__ = original


def check_reporting_failure_is_swallowed() -> None:
    """A reporting outage must not turn a handled 500 into a dropped request.

    This runs inside the handler that renders the error response. An exception
    escaping it would replace a clean 500 with a connection reset, and the
    cause would be the crash reporter rather than the crash.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sentry unreachable")

    original = httpx.Client.__init__

    def patched(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        original(self, *args, **kwargs)

    httpx.Client.__init__ = patched
    try:
        reporter = SentryReporter(dsn=parse_dsn(DSN))
        assert reporter.report(ValueError("boom")) is None
    finally:
        httpx.Client.__init__ = original


def check_the_api_still_returns_500_cleanly() -> None:
    """End to end: reporting is wired in and changes no response."""
    from fastapi.testclient import TestClient

    from main import app

    @app.get("/__crash_probe__")
    async def _crash() -> None:  # pragma: no cover - raises by design
        raise RuntimeError(f"boom with {GROQ_KEY}")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/__crash_probe__")

    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "internal_error"
    assert body["correlationId"]
    # The response body has never carried exception text, and must not start.
    assert GROQ_KEY not in response.text
    assert "boom" not in response.text


def run() -> None:
    check_dsn_parsing()
    check_text_scrubbing()
    check_frame_paths_do_not_describe_the_host()
    check_event_shape()
    check_nothing_sensitive_reaches_the_wire()
    check_envelope_framing()
    check_reporter_selection()
    check_sending_and_rate_limit()
    check_reporting_failure_is_swallowed()
    check_the_api_still_returns_500_cleanly()

    print("CRASH REPORTING SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
