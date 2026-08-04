"""CLI for the offline eval harness.

    python -m evals                          # mock provider, no gate
    python -m evals --module writing         # one module
    python -m evals --max-mae 1.0 --max-bias 0.5
    python -m evals --provider groq --yes    # billed; both flags required

The provider defaults to mock and a real provider needs `--yes` as well. An eval
run scores every case in the gold set, so a careless invocation is a burst of
billed calls, not one.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

MODULES = ("writing", "speaking")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python -m evals", description=__doc__)
    p.add_argument("--module", choices=MODULES, action="append", dest="modules")
    p.add_argument(
        "--provider",
        default="mock",
        help="mock (default) or a real provider such as groq",
    )
    p.add_argument(
        "--yes",
        action="store_true",
        help="required to run against a real, billed provider",
    )
    p.add_argument("--max-mae", type=float, default=None)
    p.add_argument(
        "--max-bias",
        type=float,
        default=None,
        help="limit on |mean signed error|; catches a systematically generous scorer",
    )
    p.add_argument("--min-within-one", type=float, default=None)
    p.add_argument(
        "--allow-failures",
        action="store_true",
        help="do not fail the run when individual cases error",
    )
    p.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    return p.parse_args(argv)


async def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.provider != "mock" and not args.yes:
        print(
            f"Refusing to run against '{args.provider}' without --yes: this would "
            f"make a billed API call for every gold case.",
            file=sys.stderr,
        )
        return 2

    # Set before importing anything that reads settings, so the provider factory
    # builds what was asked for rather than whatever .env happens to hold.
    os.environ["AI_PROVIDER"] = args.provider

    from ai.providers import build_provider  # noqa: PLC0415  (after env is set)
    from evals.harness import Gate, check_gate, format_report, run_module

    gate = Gate(
        max_mae=args.max_mae,
        max_abs_bias=args.max_bias,
        min_within_one=args.min_within_one,
        allow_failures=args.allow_failures,
    )
    gated = any(
        v is not None for v in (args.max_mae, args.max_bias, args.min_within_one)
    )

    provider = build_provider()
    modules = args.modules or list(MODULES)

    reports: list[dict[str, object]] = []
    breached = False

    for module in modules:
        metrics = await run_module(module, provider, args.provider)
        breaches = check_gate(metrics, gate)
        breached = breached or bool(breaches)

        if args.json:
            reports.append(
                {
                    "module": metrics.module,
                    "provider": metrics.provider,
                    "model": metrics.model,
                    "scored": metrics.scored,
                    "failed": metrics.failed,
                    "mae": metrics.mae,
                    "bias": metrics.bias,
                    "maxError": metrics.max_error,
                    "withinHalf": metrics.within_half,
                    "withinOne": metrics.within_one,
                    "breaches": breaches,
                    "cases": [
                        {
                            "id": r.case.id,
                            "gold": r.case.reference_band,
                            "predicted": r.predicted,
                            "error": r.error,
                        }
                        for r in metrics.results
                    ],
                }
            )
        else:
            print(format_report(metrics))
            for breach in breaches:
                print(f"  GATE FAILED: {breach}")
            print()

    if args.json:
        print(json.dumps(reports, indent=2))
        return 1 if breached else 0

    if args.provider == "mock":
        print(
            "Note: the mock provider is a heuristic stub. These numbers verify the "
            "harness and the scoring path, not the accuracy of any model."
        )
    if not gated:
        print("No thresholds given, so nothing was gated. Pass --max-mae/--max-bias to gate.")

    return 1 if breached else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
