# Load tests

```bash
# Start a backend against Postgres, with the mock AI provider.
DATABASE_URL=postgresql+asyncpg://... AI_PROVIDER=mock \
  uvicorn main:app --port 8000

# Then, from backend/:
python -m locust -f tests/load/locustfile.py --host http://localhost:8000 \
  --headless -u 20 -r 5 -t 60s
```

Exits non-zero when an objective in `slos.py` is breached, so it works as a
gate rather than as a report someone has to interpret.

## Run it against Postgres, not SQLite

SQLite serialises writes — one writer at a time, whole-database. A run against
it measures that lock, not the application: writes measured 3700ms at p95 on
SQLite under 20 users and 13ms at 3 users, which is the lock and nothing else.
This is the same reason `core/environment.py` refuses SQLite in production.

## Scoring is off by default

Every scoring request is a billed provider call, and a load test that costs
money per run is a load test nobody runs. Set `LOAD_INCLUDE_SCORING=true`
against a backend configured with `AI_PROVIDER=mock` to include them.

## What the first run found

Password hashing ran synchronously inside async handlers. Argon2 at these
parameters is ~140ms of solid CPU, so every login blocked the entire process —
not just its own request — and twenty people signing in at once queued behind
each other.

| | before | after |
|---|---|---|
| writes p95 | 3700ms | 180ms |
| auth p95 | 7500ms | 2700ms |

Moving it to a thread fixed it; Argon2 is C code that releases the GIL, so the
event loop keeps serving.

## Auth still breaches its objective, and that is left visible

2700ms against a 2000ms objective, under a synthetic burst of twenty
simultaneous registrations on a laptop also running the load generator. Real
traffic is overwhelmingly reads with occasional auth, so this profile is harder
on auth than production will be.

The objective has deliberately not been relaxed to make the run pass. An SLO
edited until it is met is not an SLO. Re-measure on real hardware against
Postgres before deciding whether the number or the service is wrong.
