"""Service level objectives.

Written down here rather than left implied, because "the API should be fast" is
not something a test can fail against and not something anyone can be held to.

The numbers are derived from what each endpoint actually does, not from a round
number that sounded reasonable:

* A **read** is one indexed query and some serialisation. On the same continent
  as the database that is tens of milliseconds; 400ms at p95 leaves room for a
  cold connection and a mobile network without hiding a genuine regression.
* A **write without AI** adds an insert and a commit. Same order of magnitude.
* A **scoring** call waits on a third-party model. Groq's own latency dominates
  by an order of magnitude, so the objective is about not adding meaningfully to
  it rather than about the total, and it is deliberately generous.
* **Auth** is slow on purpose. Argon2 is tuned to take real time, because a
  password hash that verifies in a millisecond is a password hash an attacker
  can brute-force a million times a second. This is the one endpoint where a
  fast p95 would be the bug.

Error rate is separated from latency. A service that answers every request in
50ms with a 500 satisfies any latency objective, which is why "fast" alone is
never an objective worth having.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Objective:
    name: str
    #: 95th percentile, milliseconds.
    p95_ms: int
    #: Share of requests allowed to fail, 0..1.
    error_rate: float
    why: str


#: Read endpoints: one indexed query and serialisation.
READS = Objective(
    name="reads",
    p95_ms=400,
    error_rate=0.01,
    why=(
        "One indexed query plus serialisation. Room for a cold pool connection "
        "and a mobile network, without hiding a real regression."
    ),
)

#: Writes that do not call a model.
WRITES = Objective(
    name="writes",
    p95_ms=600,
    error_rate=0.01,
    why="An insert and a commit on top of a read.",
)

#: Anything that waits on an AI provider.
SCORING = Objective(
    name="scoring",
    p95_ms=15_000,
    error_rate=0.05,
    why=(
        "Dominated by the provider's own latency by an order of magnitude. The "
        "objective is about not adding meaningfully to it, and a higher error "
        "budget reflects that a third party is in the path."
    ),
)

#: Login and registration. Slow by design.
AUTH = Objective(
    name="auth",
    p95_ms=2_000,
    error_rate=0.01,
    why=(
        "Argon2 is tuned to take real time. A password hash that verifies in a "
        "millisecond is one an attacker can try a million times a second, so a "
        "fast p95 here would be the bug."
    ),
)

ALL = (READS, WRITES, SCORING, AUTH)

#: Objective for a request tagged with a name the map does not know. Unmatched
#: traffic gets the strictest budget rather than none: an endpoint nobody
#: classified should show up as a failure, not be quietly exempt.
DEFAULT = READS


def objective_for(tag: str) -> Objective:
    for objective in ALL:
        if objective.name == tag:
            return objective
    return DEFAULT
