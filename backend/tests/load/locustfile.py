"""Load profile for the API.

    locust -f tests/load/locustfile.py --host http://localhost:8000 \
        --headless -u 20 -r 5 -t 60s

Exits non-zero when an objective in slos.py is breached, so this is usable as a
gate rather than as a report someone has to read and interpret.

Two things this deliberately does not do.

It does not hammer the scoring endpoints by default. Every scoring request is a
billed call to a real provider, and a load test that costs money per run is a
load test nobody runs. Set `LOAD_INCLUDE_SCORING=true` against a backend
configured with the mock provider to include them.

It does not create one account and reuse it. Every virtual user registers its
own, because a single account serialises on the same rows and measures lock
contention rather than throughput -- which looks like a performance problem that
does not exist in production.
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from locust import HttpUser, between, events, task  # noqa: E402

from tests.load.slos import ALL, objective_for  # noqa: E402

PASSWORD = "LoadTestPass123"
ESSAY = "Urbanisation has reshaped how populations live and work worldwide. " * 6

#: Scoring is off unless asked for: each request is a billed provider call.
INCLUDE_SCORING = os.environ.get("LOAD_INCLUDE_SCORING", "").lower() == "true"


class Learner(HttpUser):
    """One learner, doing what a learner does."""

    # A real user reads between actions. Zero wait measures how fast the server
    # can be flooded, which is a number with no operational meaning.
    wait_time = between(1, 3)

    def on_start(self) -> None:
        email = f"load-{uuid.uuid4().hex[:12]}@example.com"

        self.client.post(
            "/v1/auth/register",
            json={"fullName": "Load Tester", "email": email, "password": PASSWORD},
            name="auth",
        )
        response = self.client.post(
            "/v1/auth/login",
            json={"email": email, "password": PASSWORD},
            name="auth",
        )
        if response.status_code != 200:
            # Without a token every later request is a 401, and the run reports
            # a latency profile for an error path.
            self.environment.runner.quit()
            return

        token = response.json()["tokens"]["accessToken"]
        self.client.headers.update({"Authorization": f"Bearer {token}"})

        self.client.post(
            "/v1/onboarding",
            json={
                "examType": "academic",
                "selfLevel": "intermediate",
                "targetBand": 7.0,
                "examDate": None,
                "dailyMinutes": 30,
                "consentVoice": True,
                "consentAi": True,
            },
            name="writes",
        )

    # Weights approximate real use: people open the app and look at things far
    # more often than they submit work.
    @task(10)
    def dashboard(self) -> None:
        self.client.get("/v1/analytics/overview", name="reads")

    @task(6)
    def progress(self) -> None:
        self.client.get("/v1/analytics/progress", name="reads")

    @task(4)
    def history(self) -> None:
        self.client.get("/v1/writing/history", name="reads")

    @task(3)
    def prompts(self) -> None:
        self.client.get("/v1/writing/prompts", name="reads")

    @task(2)
    def passages(self) -> None:
        self.client.get("/v1/reading/passages", name="reads")

    @task(2)
    def recommendations(self) -> None:
        self.client.get("/v1/me/recommendations", name="reads")

    @task(1)
    def submit_essay(self) -> None:
        if not INCLUDE_SCORING:
            return
        self.client.post(
            "/v1/writing/attempts",
            json={"essayText": ESSAY, "taskType": 2, "durationSec": 900},
            name="scoring",
        )


@events.quitting.add_listener
def _check_objectives(environment, **_kwargs) -> None:
    """Fail the run when an objective is breached.

    Checked per tag rather than across the whole run: an aggregate p95 lets a
    slow endpoint hide behind a fast one, and the aggregate improves as you add
    cheap traffic, which is the opposite of a useful signal.
    """
    stats = environment.stats
    breaches: list[str] = []

    for objective in ALL:
        entry = stats.get(objective.name, "GET") or stats.get(objective.name, "POST")
        # Locust keys stats by (name, method); look across both since the same
        # tag covers reads and writes.
        matching = [
            item
            for key, item in stats.entries.items()
            if key[0] == objective.name and item.num_requests
        ]
        if not matching:
            continue

        requests = sum(item.num_requests for item in matching)
        failures = sum(item.num_failures for item in matching)
        p95 = max(item.get_response_time_percentile(0.95) or 0 for item in matching)

        if p95 > objective.p95_ms:
            breaches.append(
                f"{objective.name}: p95 {p95:.0f}ms exceeds {objective.p95_ms}ms"
            )
        rate = failures / requests if requests else 0.0
        if rate > objective.error_rate:
            breaches.append(
                f"{objective.name}: {rate:.1%} errors exceed "
                f"{objective.error_rate:.1%}"
            )

    if breaches:
        print("\nSLO BREACHES:")
        for breach in breaches:
            print(f"  - {breach}")
        environment.process_exit_code = 1
    else:
        print("\nAll objectives met.")
        environment.process_exit_code = 0
