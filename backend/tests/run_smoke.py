"""Run every smoke suite in an isolated subprocess.

Each `test_*_smoke.py` script binds the DB engine at import time from
DATABASE_URL, so suites must run in separate processes to stay isolated. This
runner gives each its own throwaway SQLite file, aggregates results, and exits
non-zero if any suite fails (used locally and in CI)."""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
TESTS_DIR = BACKEND_DIR / "tests"


def _discover() -> list[Path]:
    return sorted(TESTS_DIR.glob("test_*_smoke.py"))


def main() -> int:
    scripts = _discover()
    if not scripts:
        print("No smoke suites found.")
        return 1

    print(f"Running {len(scripts)} smoke suite(s)\n" + "=" * 48)
    failures: list[str] = []

    for script in scripts:
        db_file = BACKEND_DIR / f"ci_{uuid.uuid4().hex}.db"
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite+aiosqlite:///./{db_file.name}"
        env["PYTHONPATH"] = str(BACKEND_DIR)
        env.setdefault("PYTHONWARNINGS", "ignore::DeprecationWarning")

        # Pin the runtime the suites see. Child processes load backend/.env, so
        # without these a developer's real config leaks in: AI_PROVIDER=groq made
        # the suites issue real (billed, non-deterministic) API calls, and
        # RATE_LIMIT_ENABLED=true made request-heavy suites 429 at random.
        env["AI_PROVIDER"] = "mock"
        env["RATE_LIMIT_ENABLED"] = "false"
        env["JWT_SECRET"] = "smoke-test-secret-not-used-outside-tests"

        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(BACKEND_DIR),
            env=env,
            capture_output=True,
            text=True,
        )
        ok = result.returncode == 0
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {script.name}")
        if not ok:
            failures.append(script.name)
            print("-" * 48)
            print(result.stdout.strip()[-1500:])
            print(result.stderr.strip()[-1500:])
            print("-" * 48)

        # Clean up throwaway DB file(s).
        for leftover in BACKEND_DIR.glob(f"{db_file.stem}*"):
            leftover.unlink(missing_ok=True)

    print("=" * 48)
    if failures:
        print(f"FAILED: {len(failures)}/{len(scripts)} -> {', '.join(failures)}")
        return 1
    print(f"ALL {len(scripts)} SMOKE SUITES PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
