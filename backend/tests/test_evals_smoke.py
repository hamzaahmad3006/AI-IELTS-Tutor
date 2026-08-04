"""Smoke test: the offline eval harness, its metrics and its gate.

The metric and gate maths is checked against synthetic results, where the right
answer is known by construction. The harness is then run over the real gold set
with the mock provider to prove the end-to-end path works -- not to assert any
particular accuracy, which the mock cannot demonstrate.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_evals.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from ai.providers import build_provider  # noqa: E402
from evals import harness  # noqa: E402
from evals.harness import (  # noqa: E402
    CaseResult,
    Gate,
    GoldCase,
    check_gate,
    format_report,
    load_gold,
    run_module,
    summarise,
)

MODULES = ("writing", "speaking")


def _result(gold: float, predicted: float | None, error: str | None = None) -> CaseResult:
    return CaseResult(
        case=GoldCase(id=f"c{gold}-{predicted}", text="x", reference_band=gold, notes=""),
        predicted=predicted,
        error=error,
    )


def check_metrics() -> None:
    # Errors of +1.0, -1.0, +0.5, 0.0: MAE 0.625, bias +0.125.
    m = summarise(
        "writing",
        "mock",
        "m",
        [_result(6.0, 7.0), _result(6.0, 5.0), _result(6.0, 6.5), _result(6.0, 6.0)],
    )
    assert m.mae == 0.625, m.mae
    assert m.bias == 0.125, m.bias
    assert m.max_error == 1.0
    assert m.within_half == 0.5  # only +0.5 and 0.0 qualify
    assert m.within_one == 1.0
    assert (m.scored, m.failed) == (4, 0)

    # Bias must separate a scorer that is wrong in both directions from one that
    # is consistently generous: same MAE, very different failure mode.
    scattered = summarise("writing", "mock", "m", [_result(6.0, 7.0), _result(6.0, 5.0)])
    generous = summarise("writing", "mock", "m", [_result(6.0, 7.0), _result(6.0, 7.0)])
    assert scattered.mae == generous.mae == 1.0
    assert scattered.bias == 0.0 and generous.bias == 1.0

    # A crash is counted and listed, but kept out of the averages: otherwise a
    # broken run reads as a merely inaccurate one.
    mixed = summarise(
        "writing", "mock", "m", [_result(6.0, 6.5), _result(6.0, None, "boom")]
    )
    assert (mixed.scored, mixed.failed) == (1, 1)
    assert mixed.mae == 0.5
    assert len(mixed.failures) == 1

    empty = summarise("writing", "mock", "m", [_result(6.0, None, "boom")])
    assert empty.mae is None and empty.scored == 0

    assert "MAE" in format_report(m)
    assert "boom" in format_report(mixed)


def check_gate_logic() -> None:
    clean = summarise("writing", "mock", "m", [_result(6.0, 6.5), _result(6.0, 5.5)])
    assert check_gate(clean, Gate()) == []  # no thresholds, nothing to breach
    assert check_gate(clean, Gate(max_mae=1.0)) == []
    assert check_gate(clean, Gate(max_mae=0.1)) != []

    # Bias is absolute: a harsh scorer breaches the same limit as a generous one.
    harsh = summarise("writing", "mock", "m", [_result(7.0, 6.0), _result(7.0, 6.0)])
    assert check_gate(harsh, Gate(max_abs_bias=0.5)) != []
    assert "harsh" in check_gate(harsh, Gate(max_abs_bias=0.5))[0]
    generous = summarise("writing", "mock", "m", [_result(6.0, 7.0), _result(6.0, 7.0)])
    assert "generous" in check_gate(generous, Gate(max_abs_bias=0.5))[0]

    assert check_gate(clean, Gate(min_within_one=1.0)) == []
    wide = summarise("writing", "mock", "m", [_result(6.0, 8.0), _result(6.0, 6.0)])
    assert check_gate(wide, Gate(min_within_one=1.0)) != []

    # A failed case breaches by default -- a run that could not score is not a
    # run that passed.
    broken = summarise("writing", "mock", "m", [_result(6.0, None, "boom")])
    assert check_gate(broken, Gate()) != []
    assert "no cases scored" in " ".join(check_gate(broken, Gate(allow_failures=True)))


def check_gold_sets(tmp_dir: str) -> None:
    for module in MODULES:
        cases = load_gold(module)
        assert len(cases) >= 5, module
        ids = [c.id for c in cases]
        assert len(set(ids)) == len(ids), module
        bands = [c.reference_band for c in cases]
        # A gold set clustered in one place cannot reveal a scorer that
        # regresses to the mean, which is the most likely failure.
        assert min(bands) <= 5.0 and max(bands) >= 7.5, bands
        for c in cases:
            assert 0 <= c.reference_band <= 9
            assert c.reference_band * 2 % 1 == 0, f"{c.id}: not a half band"
            assert len(c.text.split()) >= 60, c.id
            assert c.notes, f"{c.id} has no rationale for its reference band"

    # Malformed input fails loudly rather than silently shrinking the gold set.
    original = harness.GOLD_DIR
    try:
        harness.GOLD_DIR = Path(tmp_dir)
        (harness.GOLD_DIR / "bad.jsonl").write_text("{not json", encoding="utf-8")
        for name, body in (
            ("bad", None),
            ("missing", '{"id": "a", "text": "t"}'),
            ("empty", "\n\n"),
            ("dupe", '{"id":"a","text":"t","reference_band":6}\n{"id":"a","text":"t","reference_band":7}'),
        ):
            if body is not None:
                (harness.GOLD_DIR / f"{name}.jsonl").write_text(body, encoding="utf-8")
            try:
                load_gold(name)
            except (ValueError, KeyError):
                pass
            else:  # pragma: no cover
                raise AssertionError(f"{name}.jsonl should not have loaded")

        try:
            load_gold("nonexistent")
        except FileNotFoundError:
            pass
        else:  # pragma: no cover
            raise AssertionError("a missing gold set should raise")
    finally:
        harness.GOLD_DIR = original


async def check_end_to_end() -> None:
    provider = build_provider()
    for module in MODULES:
        metrics = await run_module(module, provider, "mock")
        assert metrics.failed == 0, [f.error for f in metrics.failures]
        assert metrics.scored == len(load_gold(module))
        assert metrics.mae is not None and metrics.bias is not None
        assert metrics.model == "mock-heuristic", metrics.model
        for r in metrics.results:
            assert r.predicted is not None
            assert 0 <= r.predicted <= 9
            assert r.predicted * 2 % 1 == 0, f"{r.case.id}: not a half band"

        # A loose gate must pass on a working run. It is deliberately loose:
        # under the mock this only proves the scoring path is intact, and
        # tightening it would assert an accuracy the stub cannot support.
        assert check_gate(metrics, Gate(max_mae=1.5, max_abs_bias=1.0)) == []


def run() -> None:
    import tempfile

    check_metrics()
    check_gate_logic()
    with tempfile.TemporaryDirectory() as tmp:
        check_gold_sets(tmp)
    asyncio.run(check_end_to_end())

    print("EVALS SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
