"""Run the data retention sweep.

    python scripts/run_retention.py              # dry run: reports, changes nothing
    python scripts/run_retention.py --apply      # actually deletes

Dry run is the default and --apply is the only way past it. This is the one
script in the repo whose purpose is destroying data; making the destructive path
the one you have to type out is worth the extra word.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.retention import RetentionPolicy, sweep  # noqa: E402
from db.session import SessionLocal  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--apply", action="store_true", help="perform the deletions (default: dry run)"
    )
    p.add_argument("--ai-anonymise-days", type=int, default=None)
    p.add_argument("--ai-delete-days", type=int, default=None)
    p.add_argument("--refresh-grace-days", type=int, default=None)
    p.add_argument("--resolved-weakness-days", type=int, default=None)
    return p.parse_args(argv)


async def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    defaults = RetentionPolicy()
    policy = RetentionPolicy(
        ai_anonymise_after_days=args.ai_anonymise_days
        if args.ai_anonymise_days is not None
        else defaults.ai_anonymise_after_days,
        ai_delete_after_days=args.ai_delete_days
        if args.ai_delete_days is not None
        else defaults.ai_delete_after_days,
        refresh_grace_days=args.refresh_grace_days
        if args.refresh_grace_days is not None
        else defaults.refresh_grace_days,
        resolved_weakness_after_days=args.resolved_weakness_days
        if args.resolved_weakness_days is not None
        else defaults.resolved_weakness_after_days,
    )

    async with SessionLocal() as session:
        report = await sweep(session, policy=policy, apply=args.apply)

    print(report.describe())
    for label, cutoff in sorted(report.cutoffs.items()):
        print(f"  cutoff {label}: {cutoff.isoformat()}")

    if not args.apply and report.total:
        print("\nNothing was changed. Re-run with --apply to perform the sweep.")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
