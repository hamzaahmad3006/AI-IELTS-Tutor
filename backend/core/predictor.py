"""Transparent band-prediction heuristics (SRS section 25.5 & Appendix P).

Pure functions over (timestamp, band) history — no DB or AI dependency. Designed
to be swapped for a learned model later without changing callers."""

from __future__ import annotations

from datetime import datetime


def round_half(value: float) -> float:
    """Round to the nearest 0.5 band, clamped to [0, 9]."""
    return max(0.0, min(9.0, round(value * 2) / 2))


def _weeks_since_first(points: list[tuple[datetime, float]]) -> list[float]:
    first = points[0][0]
    return [max(0.0, (ts - first).total_seconds() / (7 * 24 * 3600)) for ts, _ in points]


def velocity_per_week(points: list[tuple[datetime, float]]) -> float:
    """Least-squares slope of band vs. weeks. 0 when fewer than 2 points."""
    n = len(points)
    if n < 2:
        return 0.0
    xs = _weeks_since_first(points)
    ys = [band for _, band in points]
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    var_x = sum((x - mean_x) ** 2 for x in xs)
    if var_x == 0:
        return 0.0
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    return cov / var_x


def project(current: float, velocity: float, weeks_ahead: float) -> float:
    """Project a future band from the current band and weekly velocity."""
    return round_half(current + velocity * weeks_ahead)


def confidence(bands: list[float]) -> float:
    """Confidence in [0, 0.95] from sample size and consistency (low variance)."""
    n = len(bands)
    if n == 0:
        return 0.0
    if n == 1:
        return 0.4
    mean = sum(bands) / n
    variance = sum((b - mean) ** 2 for b in bands) / n
    sample_factor = min(0.5, 0.1 * n)
    consistency = max(0.0, 0.45 - variance * 0.15)
    return round(min(0.95, 0.3 + sample_factor + consistency), 2)
