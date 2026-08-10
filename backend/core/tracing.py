"""Distributed tracing.

Metrics say a request was slow. A trace says which part of it was, which for
this app is almost always the question worth asking: a writing submission that
takes four seconds is either the model thinking or the database struggling, and
those need completely different fixes.

Off unless an endpoint is configured. Tracing with nowhere to send spans still
costs the work of creating them, and a service that quietly buffers spans into a
queue nobody drains is a memory leak with good intentions.

Two things are deliberately not traced.

Health and metrics endpoints are excluded. They are polled every few seconds
forever and would dominate every trace view while carrying no information.

Span attributes never include request bodies, essay text or transcripts.
Tracing backends are typically read by more people than the database is, kept
for months, and searched -- a learner's essay in a span attribute is a copy of
their work somewhere nobody expects it to be.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("tracing")

#: Paths never worth a span: polled constantly, and their latency is not a
#: question anyone asks.
EXCLUDED_PATHS = "/health,/ready,/metrics"


def configure_tracing(app: object) -> bool:
    """Install tracing if an endpoint is configured. Returns whether it was.

    Import failures and exporter problems are caught and logged rather than
    raised. Telemetry is not worth taking the service down for -- a deployment
    that will not start because its tracing backend moved is a worse outage
    than having no traces.
    """
    from core.config import get_settings

    settings = get_settings()
    endpoint = (settings.otel_endpoint or "").strip()
    if not endpoint:
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as exc:  # pragma: no cover - depends on the environment
        logger.warning("tracing unavailable: %s", exc)
        return False

    try:
        provider = TracerProvider(
            resource=Resource.create(
                {
                    "service.name": settings.otel_service_name,
                    # The environment is on the resource rather than on each
                    # span: a trace view that cannot separate staging from
                    # production shows both and is worse than useless.
                    "deployment.environment": settings.app_env,
                }
            )
        )
        # Batched, not simple. A span exported synchronously puts the tracing
        # backend's latency inside the request it is measuring, which is both
        # circular and a way to make an outage worse.
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
        )
        trace.set_tracer_provider(provider)

        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls=EXCLUDED_PATHS,
        )
    except Exception as exc:  # noqa: BLE001 - telemetry must never be fatal
        logger.warning("tracing failed to start: %s", exc)
        return False

    logger.info(
        "tracing enabled",
        extra={"endpoint": endpoint, "service": settings.otel_service_name},
    )
    return True


def current_trace_id() -> str | None:
    """The active trace id, for putting in a log line or an error response.

    This is what makes a trace findable: a user reporting "it was slow at 3pm"
    is unactionable, and a correlation id they can quote is not.
    """
    try:
        from opentelemetry import trace
    except ImportError:  # pragma: no cover
        return None

    span = trace.get_current_span()
    context = span.get_span_context()
    if not context.is_valid:
        return None
    return format(context.trace_id, "032x")
