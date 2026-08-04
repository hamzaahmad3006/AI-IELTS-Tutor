"""Domain exception taxonomy behind the RFC 7807 error contract.

Every error a client sees carries a stable, machine-readable `code`. Before
this, every `HTTPException` collapsed to `code: "http_error"`, so a mobile
client could not tell "this attempt does not exist" from "you already submitted
this" from "the content bank is empty" without string-matching the title — which
breaks the moment the wording is improved.

Codes are part of the API contract: rename one and clients break, so they are
defined here rather than typed inline at each raise site.
"""

from __future__ import annotations

from typing import Any

_TYPE_BASE = "https://errors.aitutor.app"


class AppError(Exception):
    """Base for every error that is safe to show a client verbatim."""

    status: int = 500
    code: str = "internal_error"
    title: str = "Something went wrong"

    def __init__(
        self,
        title: str | None = None,
        *,
        meta: dict[str, Any] | None = None,
    ) -> None:
        self.title = title or self.title
        self.meta = meta or {}
        super().__init__(self.title)

    @property
    def type_uri(self) -> str:
        return f"{_TYPE_BASE}/{self.code}"

    def to_problem(self, correlation_id: str) -> dict[str, Any]:
        problem: dict[str, Any] = {
            "type": self.type_uri,
            "title": self.title,
            "status": self.status,
            "code": self.code,
            "correlationId": correlation_id,
        }
        problem.update(self.meta)
        return problem


# ---------- 4xx ----------
class ValidationError(AppError):
    status = 422
    code = "validation"
    title = "Validation failed"


class AuthenticationError(AppError):
    status = 401
    code = "unauthenticated"
    title = "Sign in to continue"


class InvalidCredentialsError(AuthenticationError):
    code = "invalid_credentials"
    title = "Email or password is incorrect"


class TokenExpiredError(AuthenticationError):
    code = "token_expired"
    title = "Your session has expired"


class PermissionDeniedError(AppError):
    status = 403
    code = "forbidden"
    title = "You do not have access to this"


class NotFoundError(AppError):
    status = 404
    code = "not_found"
    title = "Not found"


class ConflictError(AppError):
    status = 409
    code = "conflict"
    title = "That conflicts with the current state"


class AlreadyExistsError(ConflictError):
    code = "already_exists"
    title = "That already exists"


class AlreadySubmittedError(ConflictError):
    code = "already_submitted"
    title = "This has already been submitted"


class PreconditionError(ConflictError):
    code = "precondition_failed"
    title = "Something needs doing first"


class RateLimitedError(AppError):
    status = 429
    code = "rate_limited"
    title = "Too many requests. Please slow down."


# ---------- 5xx ----------
class UpstreamError(AppError):
    status = 502
    code = "upstream_error"
    title = "An upstream service failed"


class ScoringUnavailableError(AppError):
    status = 503
    code = "scoring_unavailable"
    title = "AI scoring is unavailable right now"


class ContentUnavailableError(AppError):
    status = 503
    code = "content_unavailable"
    title = "That content is not available yet"


#: Codes for bare HTTPExceptions raised by FastAPI itself or by call sites not
#: yet migrated. Mapping by status is far better than one blanket "http_error":
#: a client can branch on `not_found` without knowing which handler raised it.
STATUS_CODES: dict[int, str] = {
    400: "bad_request",
    401: "unauthenticated",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation",
    429: "rate_limited",
    500: "internal_error",
    502: "upstream_error",
    503: "service_unavailable",
    504: "upstream_timeout",
}


def code_for_status(status: int) -> str:
    if status in STATUS_CODES:
        return STATUS_CODES[status]
    if 400 <= status < 500:
        return "client_error"
    return "server_error"


def type_for_code(code: str) -> str:
    # `about:blank` is the RFC 7807 default and carries no information; a real
    # URI gives the code somewhere to be documented.
    return f"{_TYPE_BASE}/{code}"
