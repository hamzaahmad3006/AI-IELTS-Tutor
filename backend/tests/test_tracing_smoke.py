"""Smoke test: tracing installs, stays out of the way, and never breaks a boot.

The assertions are mostly about tracing *not* happening: not enabled without an
endpoint, not fatal when the exporter is unreachable, and not attached to the
endpoints that are polled every few seconds forever.

Telemetry that takes a service down is worse than no telemetry, and a trace view
drowned in health checks is worse than an empty one.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_tracing.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from core.config import Settings, get_settings  # noqa: E402
from core.tracing import (  # noqa: E402
    EXCLUDED_PATHS,
    configure_tracing,
    current_trace_id,
)
from main import app  # noqa: E402


def check_disabled_without_an_endpoint() -> None:
    """The default. Spans with nowhere to go are work plus a growing buffer."""
    settings = get_settings()
    assert settings.otel_endpoint == "", "test environment should not configure OTLP"

    assert configure_tracing(FastAPI()) is False

    # And with no provider installed there is no trace to report.
    assert current_trace_id() is None


def check_unreachable_exporter_does_not_break_startup() -> None:
    """A tracing backend that moved must not stop the service booting.

    The exporter is batched and lazy, so an unreachable endpoint is discovered
    on the first flush rather than at configure time -- which is exactly the
    behaviour wanted. Either way, configure must return rather than raise.
    """
    original = get_settings
    try:
        import core.tracing as tracing_module

        fake = Settings(
            otel_endpoint="http://127.0.0.1:1/v1/traces",
            otel_service_name="test-service",
        )
        tracing_module.get_settings = lambda: fake  # type: ignore[attr-defined]

        probe = FastAPI()

        @probe.get("/ping")
        def ping() -> dict[str, str]:
            return {"ok": "yes"}

        # Must not raise, whatever it returns.
        configure_tracing(probe)

        with TestClient(probe) as client:
            # And the app still serves. A span failing to export is not a
            # reason for a request to fail.
            assert client.get("/ping").status_code == 200
    finally:
        import core.tracing as tracing_module

        tracing_module.get_settings = original  # type: ignore[attr-defined]


def check_noisy_paths_are_excluded() -> None:
    """Health and metrics are polled forever and carry no information.

    Left in, they dominate every trace view: at one probe every few seconds
    they outnumber real traffic by orders of magnitude on a quiet service.
    """
    excluded = {path.strip() for path in EXCLUDED_PATHS.split(",")}
    assert {"/health", "/ready", "/metrics"} <= excluded


def check_app_still_works() -> None:
    """The real app, with tracing off, behaves exactly as before."""
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 200
        assert client.get("/metrics").status_code == 200


def check_spans_are_actually_produced() -> None:
    """Tracing that installs cleanly and emits nothing is the failure to fear.

    Asserted against an in-memory exporter rather than a real backend, so this
    proves the instrumentation works without needing somewhere to send spans.
    """
    from opentelemetry import trace
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        SimpleSpanProcessor,
        SpanExporter,
        SpanExportResult,
    )

    captured: list[str] = []

    class Collector(SpanExporter):
        def export(self, spans):  # type: ignore[no-untyped-def]
            captured.extend(span.name for span in spans)
            return SpanExportResult.SUCCESS

        def shutdown(self) -> None:
            return None

    provider = TracerProvider(resource=Resource.create({"service.name": "probe"}))
    provider.add_span_processor(SimpleSpanProcessor(Collector()))
    trace.set_tracer_provider(provider)

    probe = FastAPI()

    @probe.get("/work")
    def work() -> dict[str, str | None]:
        # Available inside the handler, which is what makes a trace findable
        # from a log line or an error response.
        return {"traceId": current_trace_id()}

    @probe.get("/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    FastAPIInstrumentor.instrument_app(probe, excluded_urls=EXCLUDED_PATHS)

    with TestClient(probe) as client:
        body = client.get("/work").json()
        client.get("/health")

    assert any("/work" in name for name in captured), captured
    # Polled every few seconds forever; left in, they outnumber real traffic by
    # orders of magnitude and drown the trace view.
    assert not any("health" in name for name in captured), captured

    trace_id = body["traceId"]
    assert trace_id and len(trace_id) == 32, trace_id
    assert int(trace_id, 16) != 0, "an all-zero trace id means no active span"


def check_settings_defaults() -> None:
    fresh = Settings()
    # Off by default and named, so enabling it is a deliberate act rather than
    # something inherited from a stray environment variable.
    assert fresh.otel_endpoint == ""
    assert fresh.otel_service_name


def run() -> None:
    check_disabled_without_an_endpoint()
    check_unreachable_exporter_does_not_break_startup()
    check_noisy_paths_are_excluded()
    check_spans_are_actually_produced()
    check_app_still_works()
    check_settings_defaults()

    print("TRACING SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
