"""Test environment pin. Import this first, before anything reads settings.

`run_smoke.py` sets these for the suites it launches, but a suite run directly --
`python tests/test_writing_smoke.py`, which is the normal way to debug one --
inherited `.env` instead and made real, billed API calls. That happened, and it
cost quota that belonged to a person, not a budget.

The guard therefore lives in the suites themselves. The runner keeps its own
copy so the two are independent: neither is load-bearing alone.
"""

from __future__ import annotations

import os

# Set, not setdefault: an AI_PROVIDER inherited from .env is exactly the value
# that must not win here.
os.environ["AI_PROVIDER"] = "mock"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ.setdefault("JWT_SECRET", "smoke-test-secret-not-used-outside-tests")
