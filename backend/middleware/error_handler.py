"""Global exception handling producing RFC 7807 problem+json responses."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.rate_limit import RateLimitExceeded


def _correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(
        request: Request, exc: RateLimitExceeded
    ) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={
                "type": "https://errors.aitutor.app/rate_limited",
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
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "type": "about:blank",
                "title": str(exc.detail),
                "status": exc.status_code,
                "code": "http_error",
                "correlationId": _correlation_id(request),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "type": "https://errors.aitutor.app/validation",
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
        return JSONResponse(
            status_code=500,
            content={
                "type": "about:blank",
                "title": "Internal server error",
                "status": 500,
                "code": "internal_error",
                "correlationId": _correlation_id(request),
            },
        )
