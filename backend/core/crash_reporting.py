"""Crash reporting to Sentry.

Written against Sentry's envelope endpoint with httpx rather than through
`sentry-sdk`, and for once the reason is not dependency weight.

The SDK's value is what it collects automatically: local variables in every
stack frame, request bodies, headers, environment. In this application those
are, respectively, the learner's essay, the essay again, the bearer token, and
the Groq API key. Automatic capture is the feature, and here it is the hazard.

So this builds the payload by **allowlist**. Nothing reaches Sentry unless it
is named below: exception type, a scrubbed message, stack frames reduced to
file/function/line, the route template, the correlation id, and the
environment. There is no path by which an essay, a transcript, a password or a
token can be attached, because there is no code that attaches anything else.

That inverts the usual arrangement, where a denylist of sensitive keys is
maintained forever and loses to the first field nobody thought of. A denylist
has to be right every time; an allowlist has to be right once.

Disabled with no DSN, which is the default. `SENTRY_DSN` is the whole
configuration.
"""

from __future__ import annotations

import json
import re
import time
import traceback
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

BACKEND_ROOT = Path(__file__).resolve().parent.parent

#: Longest message forwarded. An exception carrying a whole essay is the case
#: this exists for -- truncation bounds the damage when a message interpolates
#: something it should not have.
MAX_MESSAGE = 500

#: Deepest stack sent. The frames nearest the raise are the informative ones.
MAX_FRAMES = 40

#: Events per window, per process. A crash loop otherwise turns one bug into a
#: quota exhaustion and a bill, and the thousandth copy of a traceback says
#: nothing the first did not.
RATE_LIMIT = 20
RATE_WINDOW_S = 60.0


class DsnError(ValueError):
    pass


@dataclass(frozen=True)
class Dsn:
    public_key: str
    project_id: str
    envelope_url: str

    @property
    def auth_header(self) -> str:
        return (
            "Sentry sentry_version=7, "
            f"sentry_key={self.public_key}, "
            "sentry_client=ielts-tutor/1.0"
        )


def parse_dsn(dsn: str) -> Dsn:
    """Split a Sentry DSN into the ingest URL and the public key.

    Shape is `https://<public_key>@<host>/<project_id>`. Parsed rather than
    pattern-matched loosely, because a malformed DSN that still "works" sends
    crash reports somewhere nobody is watching.
    """
    match = re.fullmatch(
        r"(?P<scheme>https?)://(?P<key>[^:@/]+)(?::[^@]*)?@(?P<host>[^/]+)/(?P<project>\d+)",
        (dsn or "").strip(),
    )
    if not match:
        raise DsnError("Malformed Sentry DSN")
    return Dsn(
        public_key=match.group("key"),
        project_id=match.group("project"),
        envelope_url=(
            f"{match.group('scheme')}://{match.group('host')}"
            f"/api/{match.group('project')}/envelope/"
        ),
    )


# --------------------------------------------------------------------------
# Scrubbing
# --------------------------------------------------------------------------

#: Patterns applied to any free text that does get forwarded -- exception
#: messages, mostly. The allowlist already keeps structured user data out; this
#: is the second line, for a secret interpolated into a message by code that
#: had no idea it was doing so.
#: Order is load-bearing. The connection-string rule has to run before the
#: email rule, because `user:password@host` ends in something an email pattern
#: happily matches -- it would rewrite the password half to "[email]", pass a
#: naive "is the password gone?" check, and leave the rule below dead.
_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # A postgres/redis URL carries the password in the netloc.
    (re.compile(r"\b(\w+)://[^\s:/@]+:[^\s@]+@"), r"\1://[credentials]@"),
    # Email.
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[email]"),
    # A JWT -- access and refresh tokens both. Three base64url runs.
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"), "[jwt]"),
    # Provider keys that announce themselves with a prefix.
    (re.compile(r"\b(?:gsk|sk|pk|rk)[-_][A-Za-z0-9_-]{12,}"), "[api-key]"),
    # Bearer credentials in a stringified header.
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}"), "Bearer [redacted]"),
    # Any long unbroken token -- a hex digest, a session id, a signature.
    (re.compile(r"\b[A-Fa-f0-9]{32,}\b"), "[hash]"),
)


def scrub_text(value: str) -> str:
    """Redact anything that looks like a credential, then bound the length."""
    if not value:
        return ""
    for pattern, replacement in _PATTERNS:
        value = pattern.sub(replacement, value)
    if len(value) > MAX_MESSAGE:
        # Reported rather than silently cut, so a truncated message is not
        # mistaken for the whole one during an investigation.
        value = value[:MAX_MESSAGE] + f"... [truncated, {len(value)} chars]"
    return value


def relative_frame_path(filename: str) -> tuple[str, bool]:
    """Path relative to the backend root, and whether it is our own code.

    Absolute paths describe the deployment: the operator's home directory, the
    container layout, sometimes a username. None of that helps read a
    traceback, and it is a free description of the host to anyone who reaches
    the Sentry project.

    The flag falls out of the same test rather than being guessed from the
    string afterwards -- a path that resolved inside the backend root is ours
    by definition.
    """
    try:
        relative = Path(filename).resolve().relative_to(BACKEND_ROOT)
    except (ValueError, OSError):
        # Site-packages, stdlib, or a path that does not resolve. Keep the tail
        # only: enough to identify the library, nothing about the filesystem.
        return Path(filename).name, False
    text = str(relative).replace("\\", "/")
    # The venv lives under the backend root, so resolving cleanly is not by
    # itself enough to call a frame ours.
    return text, not text.startswith((".venv/", "venv/"))


def build_frames(exc: BaseException) -> list[dict[str, Any]]:
    """Stack frames, reduced to what identifies the line of code.

    Deliberately no `vars`. Sentry renders local variables per frame when they
    are supplied, and in this codebase the locals at a crash site are the essay
    being scored, the transcript being highlighted, or the settings object with
    every API key on it.
    """
    frames: list[dict[str, Any]] = []
    for frame in traceback.extract_tb(exc.__traceback__):
        path, in_app = relative_frame_path(frame.filename)
        frames.append(
            {
                "filename": path,
                "function": frame.name,
                "lineno": frame.lineno,
                # Drives Sentry's grouping: third-party frames fold away, so
                # the ours-versus-theirs distinction is visible at a glance.
                "in_app": in_app,
            }
        )
    return frames[-MAX_FRAMES:]


def build_event(
    exc: BaseException,
    *,
    correlation_id: str = "",
    route: str = "",
    method: str = "",
    environment: str = "development",
    release: str = "",
    event_id: str | None = None,
    timestamp: float | None = None,
) -> dict[str, Any]:
    """Assemble the payload. Everything Sentry receives originates here.

    `route` must be the route *template* (`/v1/writing/attempts/{id}`), not the
    request path: a path carries ids, and ids are how a report gets tied back
    to a person.
    """
    chain: list[dict[str, Any]] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    # Walk the __cause__ chain so "X while handling Y" survives, which is
    # usually where the real fault is. Guarded against a cycle, which a
    # hand-built chain can contain.
    while current is not None and id(current) not in seen and len(chain) < 5:
        seen.add(id(current))
        chain.append(
            {
                "type": type(current).__name__,
                "value": scrub_text(str(current)),
                "stacktrace": {"frames": build_frames(current)},
            }
        )
        current = current.__cause__ or current.__context__

    # Sentry renders the last entry as the outermost exception.
    chain.reverse()

    event: dict[str, Any] = {
        "event_id": event_id or uuid.uuid4().hex,
        "timestamp": timestamp if timestamp is not None else time.time(),
        "platform": "python",
        "level": "error",
        "environment": environment,
        "exception": {"values": chain},
        # The correlation id is the join back to our own logs, which is where
        # the detail lives. Sentry gets the pointer, not the data.
        "tags": {k: v for k, v in (("correlation_id", correlation_id),) if v},
    }
    if release:
        event["release"] = release
    if route:
        event["transaction"] = f"{method} {route}".strip()
    return event


def to_envelope(event: dict[str, Any]) -> bytes:
    """Sentry's envelope framing: three newline-delimited JSON documents."""
    body = json.dumps(event, separators=(",", ":"), default=str)
    header = json.dumps(
        {"event_id": event["event_id"], "sent_at": _iso_now()},
        separators=(",", ":"),
    )
    item = json.dumps(
        {"type": "event", "length": len(body.encode("utf-8"))},
        separators=(",", ":"),
    )
    return f"{header}\n{item}\n{body}".encode("utf-8")


def _iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# --------------------------------------------------------------------------
# Reporters
# --------------------------------------------------------------------------


class NullReporter:
    """What runs when no DSN is configured, which is the default.

    A no-op rather than an optional call site: the exception handler should not
    have to know whether reporting is on, and a missing DSN must never be able
    to turn a handled 500 into an unhandled one.
    """

    enabled = False
    name = "null"

    def report(self, exc: BaseException, **_: Any) -> str | None:
        return None


@dataclass
class SentryReporter:
    dsn: Dsn
    environment: str = "development"
    release: str = ""
    timeout_s: float = 3.0

    enabled: bool = field(default=True, init=False)
    name: str = field(default="sentry", init=False)

    _sent: list[float] = field(default_factory=list, init=False)

    def _within_rate_limit(self, now: float) -> bool:
        self._sent = [t for t in self._sent if now - t < RATE_WINDOW_S]
        if len(self._sent) >= RATE_LIMIT:
            return False
        self._sent.append(now)
        return True

    def report(
        self,
        exc: BaseException,
        *,
        correlation_id: str = "",
        route: str = "",
        method: str = "",
    ) -> str | None:
        """Send one event. Returns its id, or None if nothing was sent.

        Never raises. This is called from the handler that turns a crash into
        a 500 response; an exception escaping here would replace a handled
        error with an unhandled one, and the user would get a dropped
        connection because the *reporting* failed.
        """
        now = time.time()
        if not self._within_rate_limit(now):
            return None
        try:
            event = build_event(
                exc,
                correlation_id=correlation_id,
                route=route,
                method=method,
                environment=self.environment,
                release=self.release,
                timestamp=now,
            )
            with httpx.Client(timeout=self.timeout_s) as client:
                client.post(
                    self.dsn.envelope_url,
                    content=to_envelope(event),
                    headers={
                        "Content-Type": "application/x-sentry-envelope",
                        "X-Sentry-Auth": self.dsn.auth_header,
                    },
                )
            return event["event_id"]
        except Exception:  # noqa: BLE001 - see docstring
            return None


def build_reporter() -> NullReporter | SentryReporter:
    """Pick a reporter from configuration.

    A malformed DSN disables reporting rather than stopping the app. The
    trade-off is deliberate and runs the other way from the environment check
    in core/environment.py: booting without crash reports costs visibility,
    while refusing to boot over a typo in an optional integration costs the
    service.
    """
    from core.config import get_settings

    settings = get_settings()
    if not settings.sentry_dsn:
        return NullReporter()
    try:
        dsn = parse_dsn(settings.sentry_dsn)
    except DsnError:
        return NullReporter()
    return SentryReporter(
        dsn=dsn,
        environment=settings.app_env,
        release=settings.sentry_release,
    )
