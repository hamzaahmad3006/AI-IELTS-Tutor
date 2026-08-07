"""Study time, reported by the client and clamped here.

Only the client knows how long someone spent reading a passage. The server sees
one request at the end, and a request timestamp says nothing about whether the
learner was working or had the app open in a pocket.

So the number has to come from the client, and the client is not trustworthy.
Not because learners are adversarial -- almost none will be -- but because a
backgrounded app, a paused timer that never resumed, or a phone left on a desk
all produce numbers that are wrong in the same direction, and a study total
built from them is fiction presented as measurement.

Clamping is therefore not fraud prevention. It is the difference between "you
studied 40 minutes this week", which is useful, and "you studied 19 hours",
which is obviously broken and makes every other figure on the screen suspect.
"""

from __future__ import annotations

#: Longest plausible single attempt, per module, in seconds.
#:
#: Set from what the real exam allows plus generous slack, not from what a
#: determined user could sit through. A reading passage is 20 minutes in the
#: test; an hour on one is a learner taking their time, and three hours is a
#: forgotten timer.
CEILINGS = {
    "writing": 90 * 60,
    "reading": 60 * 60,
    "listening": 45 * 60,
    "speaking": 30 * 60,
}

DEFAULT_CEILING = 60 * 60

#: Below this an attempt is not study, it is a tap. Counting it would inflate
#: the total with noise while looking precise.
MIN_SECONDS = 5


def clamp(seconds: int | None, module: str) -> int:
    """Reduce a reported duration to something plausible.

    Silently, on purpose. A learner who backgrounded the app has done nothing
    wrong and does not need to be told their timer was corrected; the honest
    response is to record what is defensible and move on.
    """
    if seconds is None or seconds < MIN_SECONDS:
        return 0
    return min(int(seconds), CEILINGS.get(module, DEFAULT_CEILING))


def total_minutes(seconds: int) -> int:
    """Whole minutes, rounded to nearest.

    Rounded rather than truncated: 59 seconds of study reported as "0 minutes"
    reads as the app having lost the work, which is worse than a minute of
    imprecision in a figure nobody makes decisions on.
    """
    return round(seconds / 60)
