"""Global exception handling producing RFC 7807 problem+json responses."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.crash_reporting import build_reporter
from core.errors import AppError, code_for_status, type_for_code
from core.rate_limit import RateLimitExceeded

logger = logging.getLogger("api.error")


def _correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


def _route_template(request: Request) -> str:
    """The route pattern, never the request path.

    A path carries ids, and an id is how a crash report gets tied back to a
    person. The template groups the same bug across every learner who hit it,
    which is also what makes the report useful.
    """
    route = request.scope.get("route")
    return getattr(route, "path", "") or ""


def register_exception_handlers(app: FastAPI) -> None:
    # Built once at registration. A NullReporter when no DSN is configured,
    # so the handler below never has to know whether reporting is on.
    reporter = build_reporter()
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        # 5xx means the failure is ours; log it with enough context to trace,
        # while the client still gets a stable code rather than a bare 500.
        if exc.status >= 500:
            logger.error(
                "domain error",
                extra={
                    "code": exc.code,
                    "path": request.url.path,
                    "status": exc.status,
                },
            )
        return JSONResponse(
            status_code=exc.status,
            content=exc.to_problem(_correlation_id(request)),
        )

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(
        request: Request, exc: RateLimitExceeded
    ) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={
                "type": type_for_code("rate_limited"),
                "title": "Too many requests. Please slow down.",
                "status": 429,
                "code": "rate_limited",
                "correlationId": _correlation_id(request),
            },
            headers={
                "Retry-After": str(exc.retry_after),
                "X-RateLimit-Limit": str(exc.limit),
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
       
        code = code_for_status(exc.status_code)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "type": type_for_code(code),
                "title": str(exc.detail),
                "status": exc.status_code,
                "code": code,
                "correlationId": _correlation_id(request),
            },
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "type": type_for_code("validation"),
                "title": "Validation failed",
                "status": 422,
                "code": "validation",
                "correlationId": _correlation_id(request),
                "errors": [
                    {"field": ".".join(str(p) for p in e["loc"]), "message": e["msg"]}
                    for e in exc.errors()
                ],
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        # The exception text is never returned: it can carry connection
        # strings, SQL fragments or user data. The correlation id is how a
        # report is tied back to the logged traceback.
        logger.exception("unhandled exception", extra={"path": request.url.path})
        # Reported after logging, never instead of it: the log holds the full
        # traceback and the detail, Sentry gets the allowlisted summary and
        # the correlation id that joins the two. `report` swallows its own
        # failures, so a reporting outage cannot turn a handled 500 into a
        # dropped connection.
        reporter.report(
            exc,
            correlation_id=_correlation_id(request),
            route=_route_template(request),
            method=request.method,
        )
        return JSONResponse(
            status_code=500,
            content={
                "type": type_for_code("internal_error"),
                "title": "Internal server error",
                "status": 500,
                "code": "internal_error",
                "correlationId": _correlation_id(request),
            },
        )
