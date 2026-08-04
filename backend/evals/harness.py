"""Offline evaluation harness: score a gold set and report error metrics.

Why this exists: prompts are edited far more often than they are measured. A
reworded rubric that quietly shifts every band half a point looks fine in a
smoke test -- the response parses, the endpoint returns 200 -- and only shows up
weeks later as learners who were told they were ready and were not. This runs a
fixed set of scripts with known reference bands through the real scoring path
and reports how far off the result is.

Two honest limitations, stated up front rather than buried:

* The reference bands were calibrated against the public IELTS band descriptors.
  They are not official examiner marks, so they carry the uncertainty of any
  single rater. Treat a 0.5 difference as noise and a systematic drift as signal.
* Run against the mock provider, the numbers measure the heuristic stub, not any
  model. That run is still worth having -- it exercises the prompt, the schema
  and the rounding -- but a mock MAE says nothing about scoring quality, and the
  report labels it accordingly.

Bias is reported alongside MAE and matters more for a tutor. A scorer that is
wrong in both directions frustrates learners; a scorer that is consistently
generous tells them they are ready for an exam they will fail.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ai.orchestrator import AIOrchestrator
from ai.provider import LLMProvider

GOLD_DIR = Path(__file__).parent / "gold"

#: A band is reported to the nearest half point, so two raters can legitimately
#: differ by this much on the same script.
HALF_BAND = 0.5


@dataclass(frozen=True)
class GoldCase:
    id: str
    text: str
    reference_band: float
    notes: str
    #: Writing only.
    task_type: int | None = None
    #: Speaking only.
    part: int | None = None


@dataclass
class CaseResult:
    case: GoldCase
    predicted: float | None
    error: str | None = None

    @property
    def signed_error(self) -> float | None:
        if self.predicted is None:
            return None
        return self.predicted - self.case.reference_band

    @property
    def absolute_error(self) -> float | None:
        signed = self.signed_error
        return None if signed is None else abs(signed)


@dataclass
class Metrics:
    module: str
    provider: str
    model: str
    scored: int
    failed: int
    mae: float | None
    bias: float | None
    max_error: float | None
    within_half: float | None
    within_one: float | None
    results: list[CaseResult] = field(default_factory=list)

    @property
    def failures(self) -> list[CaseResult]:
        return [r for r in self.results if r.error is not None]


def load_gold(module: str) -> list[GoldCase]:
    """Read a gold file. A malformed line fails loudly.

    Silently skipping a bad record would shrink the gold set without saying so,
    and a gate that passes because it stopped checking things is worse than no
    gate at all.
    """
    path = GOLD_DIR / f"{module}.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"No gold set for module '{module}' at {path}")

    cases: list[GoldCase] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
            cases.append(
                GoldCase(
                    id=raw["id"],
                    text=raw["text"],
                    reference_band=float(raw["reference_band"]),
                    notes=raw.get("notes", ""),
                    task_type=raw.get("task_type"),
                    part=raw.get("part"),
                )
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"{path.name} line {lineno} is malformed: {exc}") from exc

    if not cases:
        raise ValueError(f"{path.name} contains no cases")
    ids = [c.id for c in cases]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise ValueError(f"{path.name} has duplicate case ids: {sorted(duplicates)}")
    return cases


def summarise(module: str, provider: str, model: str, results: list[CaseResult]) -> Metrics:
    """Compute metrics over the cases that scored.

    Failures are counted and listed but excluded from the averages: folding a
    crash in as a large error would let a broken run masquerade as an inaccurate
    one, and those need different fixes.
    """
    errors = [r.absolute_error for r in results if r.absolute_error is not None]
    signed = [r.signed_error for r in results if r.signed_error is not None]
    scored = len(errors)

    return Metrics(
        module=module,
        provider=provider,
        model=model,
        scored=scored,
        failed=len(results) - scored,
        mae=round(sum(errors) / scored, 3) if scored else None,
        bias=round(sum(signed) / scored, 3) if scored else None,
        max_error=round(max(errors), 3) if scored else None,
        within_half=round(
            sum(1 for e in errors if e <= HALF_BAND) / scored, 3
        )
        if scored
        else None,
        within_one=round(sum(1 for e in errors if e <= 1.0) / scored, 3)
        if scored
        else None,
        results=results,
    )


async def run_module(
    module: str, provider: LLMProvider, provider_name: str
) -> Metrics:
    """Score every gold case for one module through the real scoring path."""
    orchestrator = AIOrchestrator(provider)
    cases = load_gold(module)
    results: list[CaseResult] = []
    model = "unknown"

    for case in cases:
        try:
            if module == "writing":
                score, meta = await orchestrator.score_writing(
                    essay=case.text, task_type=case.task_type or 2
                )
            elif module == "speaking":
                score, meta = await orchestrator.score_speaking(
                    transcript=case.text, part=case.part
                )
            else:
                raise ValueError(f"No scorer for module '{module}'")
            model = meta.model or model
            results.append(CaseResult(case=case, predicted=score.overall_band))
        except Exception as exc:  # noqa: BLE001 - a failed case is a result too
            results.append(
                CaseResult(case=case, predicted=None, error=f"{type(exc).__name__}: {exc}")
            )

    return summarise(module, provider_name, model, results)


@dataclass(frozen=True)
class Gate:
    """Thresholds a run must satisfy. Absent thresholds are not checked."""

    max_mae: float | None = None
    max_abs_bias: float | None = None
    min_within_one: float | None = None
    allow_failures: bool = False


def check_gate(metrics: Metrics, gate: Gate) -> list[str]:
    """Return the breaches. An empty list means the run passed."""
    breaches: list[str] = []

    if metrics.failed and not gate.allow_failures:
        breaches.append(f"{metrics.failed} case(s) failed to score")

    if metrics.scored == 0:
        breaches.append("no cases scored")
        return breaches

    if gate.max_mae is not None and metrics.mae is not None and metrics.mae > gate.max_mae:
        breaches.append(f"MAE {metrics.mae} exceeds limit {gate.max_mae}")

    if (
        gate.max_abs_bias is not None
        and metrics.bias is not None
        and abs(metrics.bias) > gate.max_abs_bias
    ):
        direction = "generous" if metrics.bias > 0 else "harsh"
        breaches.append(
            f"bias {metrics.bias:+} ({direction}) exceeds limit "
            f"±{gate.max_abs_bias}"
        )

    if (
        gate.min_within_one is not None
        and metrics.within_one is not None
        and metrics.within_one < gate.min_within_one
    ):
        breaches.append(
            f"only {metrics.within_one:.0%} of cases within 1.0 band, "
            f"need {gate.min_within_one:.0%}"
        )

    return breaches


def format_report(metrics: Metrics) -> str:
    """Human-readable report, per case then summary."""
    lines = [
        f"{metrics.module.upper()}  provider={metrics.provider}  model={metrics.model}",
        "",
        f"  {'case':<26} {'gold':>5} {'pred':>6} {'err':>7}",
        f"  {'-' * 26} {'-' * 5} {'-' * 6} {'-' * 7}",
    ]
    for r in metrics.results:
        if r.predicted is None:
            lines.append(f"  {r.case.id:<26} {r.case.reference_band:>5.1f} {'--':>6} {'FAILED':>7}")
        else:
            lines.append(
                f"  {r.case.id:<26} {r.case.reference_band:>5.1f} "
                f"{r.predicted:>6.1f} {r.signed_error:>+7.1f}"
            )

    lines.append("")
    if metrics.scored:
        lines.append(
            f"  MAE {metrics.mae}   bias {metrics.bias:+}   worst {metrics.max_error}"
        )
        lines.append(
            f"  within 0.5 band: {metrics.within_half:.0%}   "
            f"within 1.0 band: {metrics.within_one:.0%}   "
            f"({metrics.scored} scored, {metrics.failed} failed)"
        )
    else:
        lines.append(f"  nothing scored ({metrics.failed} failed)")

    for r in metrics.failures:
        lines.append(f"  ! {r.case.id}: {r.error}")

    return "\n".join(lines)
