"""Smoke test: the Prometheus alerting rules.

The failure this exists to prevent is an alert on a metric that does not
exist. It parses, it loads, it appears in the rules list, and it can never
fire -- so it reads as coverage while providing none. That is strictly worse
than having no rule, because nobody goes looking for the gap.

`promtool check rules` cannot catch it: promtool validates syntax, and has no
idea which metrics this application actually exports. So the central assertion
here is the one promtool cannot make -- every metric named in a rule is
registered in core/metrics.py, or is one of the few that Prometheus itself
provides.

Also asserted: every alert carries a severity and a summary, and every alert
has a `for:` clause. An alert with no `for:` pages someone on a single unlucky
scrape, and alerts that cry wolf get muted.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_alerts.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

import yaml  # noqa: E402

from prometheus_client import REGISTRY  # noqa: E402

import core.metrics  # noqa: E402,F401  (registers the collectors)

RULES_PATH = Path(__file__).resolve().parent.parent / "observability" / "alerts.yml"

#: Series Prometheus generates itself, which the app therefore never exports.
PROMETHEUS_OWN = {"up"}

#: Suffixes the client library appends to a histogram or counter. The rule
#: references `http_request_duration_seconds_bucket`; what is registered is
#: `http_request_duration_seconds`.
DERIVED_SUFFIXES = ("_bucket", "_count", "_sum", "_total", "_created")

SEVERITIES = {"critical", "warning"}


def _load() -> dict:
    return yaml.safe_load(RULES_PATH.read_text(encoding="utf-8"))


def _exported_metric_names() -> set[str]:
    """Every metric name the app can actually produce, including variants.

    Read from the live registry rather than from a hand-kept list, so renaming
    a metric in core/metrics.py breaks this test instead of quietly orphaning
    an alert.
    """
    names: set[str] = set()
    for metric in REGISTRY.collect():
        names.add(metric.name)
        for sample in metric.samples:
            names.add(sample.name)
        # A counter registers as `foo` and emits `foo_total`; record both
        # directions so either spelling in a rule resolves.
        for suffix in DERIVED_SUFFIXES:
            names.add(f"{metric.name}{suffix}")
    return names


def _recorded_names(document: dict) -> set[str]:
    """Names produced by recording rules, which alerts may then reference."""
    return {
        rule["record"]
        for group in document["groups"]
        for rule in group["rules"]
        if "record" in rule
    }


#: A bare metric name in a PromQL expression: an identifier not preceded by a
#: word character, and not followed by "(", which would make it a function
#: call.
#:
#: The two negative lookaheads have to sit directly after the capture, in this
#: order. With only `(?!\s*\()` the greedy class happily backtracks -- `sum(`
#: matches as `su`, since the character after `su` is `m` rather than `(` --
#: and every function name is then reported as a missing metric. `(?![\w:])`
#: is what pins the match to the whole identifier. `:` is included there
#: because recording rules are named `job:http_errors:rate5m`, and a boundary
#: assertion would stop at the first colon.
_METRIC_TOKEN = re.compile(r"(?<![\w.:])([a-zA-Z_][a-zA-Z0-9_:]*)(?![\w:])(?!\s*\()")

#: PromQL keywords, functions and aggregation modifiers that look like metric
#: names to a regex.
_RESERVED = {
    "sum", "rate", "irate", "increase", "avg", "min", "max", "count", "by",
    "without", "on", "ignoring", "group_left", "group_right", "offset", "le",
    "histogram_quantile", "clamp_min", "clamp_max", "topk", "bottomk", "abs",
    "ceil", "floor", "round", "delta", "idelta", "deriv", "predict_linear",
    "stddev", "stdvar", "quantile", "absent", "changes", "resets", "job",
    "instance", "status", "provider", "feature", "method", "route", "and",
    "or", "unless", "bool", "time", "vector", "scalar",
}


def _metrics_in(expression: str) -> set[str]:
    # Strip label matchers first: their contents are label names and string
    # literals, not metric names.
    without_labels = re.sub(r"\{[^}]*\}", " ", expression)
    # And durations like [5m], which would otherwise read as identifiers.
    without_ranges = re.sub(r"\[[^\]]*\]", " ", without_labels)
    found = {match.group(1) for match in _METRIC_TOKEN.finditer(without_ranges)}
    return {
        name
        for name in found
        if name not in _RESERVED and not name.isdigit()
    }


def check_the_detector_works() -> None:
    """Guards the guard.

    The metric check is only worth having if the extractor is right, and its
    failure mode is silent: a regex that matches nothing reports no unknown
    metrics and passes. It also has to not report function names, or the
    signal drowns in false positives. Both directions are pinned here.
    """
    expression = (
        'sum(rate(ai_calls_total{status!="ok"}[15m]))'
        " / clamp_min(sum(rate(ai_calls_total[15m])), 0.001)"
    )
    assert _metrics_in(expression) == {"ai_calls_total"}

    # Recording-rule names survive intact rather than being cut at the colon.
    assert "job:http_errors:rate5m" in _metrics_in(
        "job:http_errors:rate5m / clamp_min(job:http_requests:rate5m, 0.001)"
    )

    # A histogram's _bucket suffix is part of the name.
    assert _metrics_in(
        "histogram_quantile(0.95, sum by (le) "
        "(rate(http_request_duration_seconds_bucket[5m])))"
    ) == {"http_request_duration_seconds_bucket"}

    # And a name that does not exist is actually reported.
    assert "definitely_not_a_metric" in _metrics_in("sum(definitely_not_a_metric[5m])")


def check_file_is_well_formed() -> None:
    document = _load()
    assert document["groups"], "no rule groups"
    names = [group["name"] for group in document["groups"]]
    assert len(names) == len(set(names)), f"duplicate group names: {names}"

    for group in document["groups"]:
        assert group.get("rules"), f"group {group['name']} has no rules"
        for rule in group["rules"]:
            # Exactly one of the two, never both -- Prometheus rejects a rule
            # that tries to be a recording rule and an alert at once.
            assert ("alert" in rule) ^ ("record" in rule), rule
            assert rule.get("expr"), rule


def check_every_metric_exists() -> None:
    """The assertion promtool cannot make."""
    document = _load()
    known = _exported_metric_names() | _recorded_names(document) | PROMETHEUS_OWN

    unknown: list[str] = []
    for group in document["groups"]:
        for rule in group["rules"]:
            label = rule.get("alert") or rule.get("record")
            for metric in _metrics_in(rule["expr"]):
                if metric not in known:
                    unknown.append(f"{label}: {metric}")

    assert not unknown, (
        "rules reference metrics this app does not export -- they would never "
        f"fire: {unknown}"
    )


def check_alerts_are_actionable() -> None:
    document = _load()
    problems: list[str] = []

    for group in document["groups"]:
        for rule in group["rules"]:
            name = rule.get("alert")
            if not name:
                continue

            # Without `for:`, one slow scrape pages someone.
            if not rule.get("for"):
                problems.append(f"{name}: no 'for' clause")

            severity = (rule.get("labels") or {}).get("severity")
            if severity not in SEVERITIES:
                problems.append(f"{name}: severity {severity!r} not in {SEVERITIES}")

            # A page with no summary is a pager buzz with no information.
            if not (rule.get("annotations") or {}).get("summary"):
                problems.append(f"{name}: no summary annotation")

    assert not problems, problems


def check_ratios_cannot_divide_by_zero() -> None:
    """0/0 is NaN, and NaN compares false against every threshold.

    An error-ratio alert that silently disables itself when traffic stops is
    exactly backwards: no traffic is when it matters most.
    """
    document = _load()
    for group in document["groups"]:
        for rule in group["rules"]:
            expression = rule["expr"]
            if "/" not in expression:
                continue
            label = rule.get("alert") or rule.get("record")
            assert "clamp_min" in expression, (
                f"{label} divides without guarding the denominator"
            )


def check_the_mock_provider_is_alerted_on() -> None:
    """The one failure that looks like success from every other angle.

    If the factory falls back to the mock in production, every learner gets an
    invented band score. Latency is fine, the error rate is zero, and nothing
    else in this file would notice.
    """
    document = _load()
    expressions = [
        rule["expr"]
        for group in document["groups"]
        for rule in group["rules"]
        if rule.get("alert")
    ]
    assert any(
        'provider="mock"' in expression for expression in expressions
    ), "nothing alerts on scores being served by the offline mock"


def run() -> None:
    check_the_detector_works()
    check_file_is_well_formed()
    check_every_metric_exists()
    check_alerts_are_actionable()
    check_ratios_cannot_divide_by_zero()
    check_the_mock_provider_is_alerted_on()

    print("ALERTS SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
