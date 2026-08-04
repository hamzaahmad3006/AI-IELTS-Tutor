"""Adaptive difficulty: recency-weighted level with hysteresis.

Replaces a flat mean of the last five bands, which had three problems:

1. A five-sessions-old band counted as much as today's, so real improvement took
   several attempts to register and one bad session dragged for a week.
2. Hard cutoffs meant a learner hovering near a boundary flipped level on almost
   every attempt. Content that changes difficulty every session is not adaptive,
   it is unstable.
3. Recorded weaknesses were ignored, so someone scraping a band 6.6 with severe
   unresolved weaknesses was promoted to hard anyway.

Everything here is a pure function so the behaviour can be tested directly,
without a database or an HTTP round trip.
"""

from __future__ import annotations

CONCRETE_DIFFICULTIES = ("easy", "medium", "hard")

#: Weight given to the newest band. 0.45 puts roughly two thirds of the weight
#: on the last three attempts while still remembering older ones.
EMA_ALPHA = 0.45

#: Band boundaries between levels.
EASY_CEILING = 5.0
MEDIUM_CEILING = 6.5

#: How far past a boundary the score must go before the level changes. Without
#: this a learner sitting on 6.5 alternates between medium and hard forever.
HYSTERESIS = 0.25

#: How many recent attempts feed the average. Older ones carry so little EMA
#: weight that including them only costs a wider query.
HISTORY_WINDOW = 8

#: Severity (0..1) at or above which a level promotion is held back. Someone
#: scoring well but making the same mistakes repeatedly is not ready to move up.
SEVERITY_BRAKE = 0.5


#: Upper band of each level. "hard" has no ceiling, so it is absent: a level
#: with no upper bound must not appear to have one.
_CEILINGS = {"easy": EASY_CEILING, "medium": MEDIUM_CEILING}


def ema(bands: list[float], alpha: float = EMA_ALPHA) -> float | None:
    """Exponentially weighted average, oldest first.

    Returns None for no data rather than a default, so callers must decide what
    "unknown" means rather than silently treating it as a score.
    """
    if not bands:
        return None
    value = bands[0]
    for band in bands[1:]:
        value = alpha * band + (1 - alpha) * value
    return value


def level_for(score: float) -> str:
    if score < EASY_CEILING:
        return "easy"
    if score <= MEDIUM_CEILING:
        return "medium"
    return "hard"


def resolve_level(
    bands: list[float],
    *,
    current: str | None = None,
    top_severity: float = 0.0,
) -> tuple[str, float | None, str]:
    """Pick a difficulty from band history.

    `current` is the level last served; supplying it enables hysteresis, so the
    level only changes when the score has clearly moved rather than jittering
    around a boundary. Returns (level, score, rationale).
    """
    score = ema(bands)
    if score is None:
        return "medium", None, "No history yet; starting at medium."

    proposed = level_for(score)

    if current in CONCRETE_DIFFICULTIES and proposed != current:
        # Require the score to clear the boundary by a margin before moving. The
        # margin applies to the boundary actually being crossed -- the ceiling
        # of the current level going up, the ceiling of the level below it
        # coming down -- not to some fixed property of the current level.
        here = CONCRETE_DIFFICULTIES.index(current)
        moving_up = CONCRETE_DIFFICULTIES.index(proposed) > here
        boundary = _CEILINGS[current] if moving_up else _CEILINGS[
            CONCRETE_DIFFICULTIES[here - 1]
        ]

        cleared = (
            score >= boundary + HYSTERESIS
            if moving_up
            else score <= boundary - HYSTERESIS
        )
        if not cleared:
            return (
                current,
                round(score, 1),
                f"Holding at {current}: recent form {score:.1f} is close to the "
                f"boundary.",
            )

    # A promotion is held back while a severe weakness is still unresolved:
    # scoring well by avoiding the thing you are bad at is not readiness.
    if (
        current in CONCRETE_DIFFICULTIES
        and top_severity >= SEVERITY_BRAKE
        and CONCRETE_DIFFICULTIES.index(proposed)
        > CONCRETE_DIFFICULTIES.index(current)
    ):
        return (
            current,
            round(score, 1),
            f"Holding at {current}: recent form {score:.1f} would move you up, "
            f"but a recurring weakness is still unresolved.",
        )

    return (
        proposed,
        round(score, 1),
        f"Recent form {score:.1f} (recency-weighted) maps to {proposed}.",
    )
