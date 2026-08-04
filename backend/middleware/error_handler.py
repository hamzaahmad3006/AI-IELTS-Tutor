"""Global exception handling producing RFC 7807 problem+json responses."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.errors import AppError, code_for_status, type_for_code
from core.rate_limit import RateLimitExceeded

logger = logging.getLogger("api.error")


def _correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


def register_exception_handlers(app: FastAPI) -> None:
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
        # Bare HTTPExceptions - raised by FastAPI itself for unmatched routes,
        # and by call sites not yet migrated - get a code derived from the
        # status. Far more useful than one blanket "http_error", which left
        # clients string-matching the title to tell errors apart.
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
