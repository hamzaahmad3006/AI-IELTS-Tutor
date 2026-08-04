"""Prometheus metrics.

Scoped deliberately. A metrics endpoint that exposes everything is not more
useful than one that exposes the right things, and it costs cardinality --
which is the usual way a Prometheus install falls over.

Two rules followed here:

* **Label on the route template, never the URL.** `/v1/writing/attempts/{id}`
  is one label value; the raw path would be one per attempt, and a few thousand
  learners would produce a time series per attempt id and take the server down.
* **No label carries user data.** No user ids, no emails, no essay text. Metrics
  are typically scraped by infrastructure with far weaker access control than
  the API, and they are retained for months.
"""

from __future__ import annotations

import time

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

#: Buckets in seconds. Chosen around what this API actually does: most reads
#: are single-digit milliseconds, an AI scoring call is seconds. The default
#: bucket set wastes resolution below 5ms where nothing happens and runs out
#: above 10s where the interesting failures are.
LATENCY_BUCKETS = (0.005, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)

REQUESTS = Counter(
    "http_requests_total",
    "HTTP requests, by route template, method and status class.",
    ["method", "route", "status"],
)

LATENCY = Histogram(
    "http_request_duration_seconds",
    "Request duration by route template.",
    ["method", "route"],
    buckets=LATENCY_BUCKETS,
)

IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Requests currently being served.",
)

AI_CALLS = Counter(
    "ai_calls_total",
    "Scoring calls, by provider and outcome.",
    ["provider", "feature", "status"],
)

AI_TOKENS = Counter(
    "ai_tokens_total",
    "Tokens consumed, by provider.",
    ["provider"],
)

AI_COST = Counter(
    "ai_cost_usd_total",
    "Estimated cumulative spend in USD, by provider. Derived from a local "
    "price table times token counts, not from provider invoices -- alert on "
    "its shape, reconcile against the real bill.",
    ["provider"],
)


#: Returned for anything that did not match a route. Scanners, typos and probes
#: for /wp-admin must collapse to one series -- labelling them with the path
#: they asked for hands anyone on the internet a way to grow the metric store
#: without limit.
UNMATCHED = "<unmatched>"


def _route_template(request: Request) -> str:
    """The full route pattern for a matched request, e.g. /v1/writing/attempts/{id}.

    Rebuilt from the request path by substituting each matched path parameter
    back into it, rather than read off the route object. Included routers are
    mounted as nested routers in this FastAPI version, so a route's own `.path`
    is relative to its mount ("/writing/prompts", missing the /v1), and the
    prefix is not recoverable from the scope -- root_path is empty. Substituting
    into the real path is the one approach that does not depend on how routers
    happen to be nested.
    """
    route = request.scope.get("route")
    if route is None:
        return UNMATCHED

    path = request.url.path
    params = request.scope.get("path_params") or {}
    if not params:
        # Nothing variable in it, so the path *is* the template.
        return path

    replacements = {str(value): f"{{{name}}}" for name, value in params.items()}
    segments = [replacements.get(seg, seg) for seg in path.split("/")]
    template = "/".join(segments)

    if any(placeholder not in template for placeholder in replacements.values()):
        # A parameter spanning multiple segments (a :path converter) did not
        # substitute cleanly. Fall back to the route's own relative template:
        # less readable, but bounded. Cardinality is the thing that breaks
        # Prometheus, so when in doubt collapse rather than describe.
        fallback = getattr(route, "path", None)
        return fallback if isinstance(fallback, str) else UNMATCHED

    return template


class MetricsMiddleware:
    """Records count, duration and in-flight depth for every request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        # The scrape itself is not interesting and would only ever measure the
        # monitoring system watching itself.
        if request.url.path == "/metrics":
            await self.app(scope, receive, send)
            return

        status_holder = {"code": 500}

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                status_holder["code"] = message["status"]
            await send(message)

        IN_PROGRESS.inc()
        method = request.method
        started = time.perf_counter()
        # Timed by hand rather than with Histogram.time(): the route label is
        # only knowable *after* the router has matched, and the context manager
        # would have to be given a label value on the way in -- which would file
        # every observation under a placeholder.
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed = time.perf_counter() - started
            IN_PROGRESS.dec()
            route = _route_template(request)
            LATENCY.labels(method=method, route=route).observe(elapsed)
            REQUESTS.labels(
                method=method, route=route, status=str(status_holder["code"])
            ).inc()


def record_ai_call(
    *, provider: str, feature: str, status: str, tokens: int, cost_usd: float
) -> None:
    """Mirror an ai_interactions row into the counters.

    The database stays the record of truth -- it is queryable per learner and
    survives a restart. These exist so spend can be alerted on, which is a thing
    you want to hear about within a minute, not at the end of the month.
    """
    AI_CALLS.labels(provider=provider, feature=feature, status=status).inc()
    if tokens:
        AI_TOKENS.labels(provider=provider).inc(tokens)
    if cost_usd:
        AI_COST.labels(provider=provider).inc(cost_usd)


def render() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
