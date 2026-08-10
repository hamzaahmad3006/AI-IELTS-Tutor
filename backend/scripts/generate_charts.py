"""Generate the Task 1 chart assets.

    python scripts/generate_charts.py            # report
    python scripts/generate_charts.py --apply    # write the SVGs

Writes into media/charts/, which the media route serves without a signature --
these are identical for every candidate, like the seeded listening clips.

Data is invented but plausible. Real published IELTS charts are copyrighted, and
a candidate who has seen the original is practising recall rather than
description.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.charts import ChartSpec, Series, describe, render  # noqa: E402

CHARTS: dict[str, ChartSpec] = {
    "transport-modes": ChartSpec(
        title="Transport used to commute in one city, 2000-2020",
        categories=["2000", "2005", "2010", "2015", "2020"],
        series=[
            Series("Bus", [45, 40, 35, 30, 25]),
            Series("Car", [30, 35, 40, 45, 50]),
            Series("Bicycle", [10, 12, 15, 18, 20]),
        ],
        y_label="Share of commuters",
        unit="%",
        kind="line",
        notes=["Figures are percentages of all commuters and do not total 100."],
    ),
    "energy-sources": ChartSpec(
        title="Electricity generation by source in two countries, 2022",
        categories=["Coal", "Gas", "Nuclear", "Hydro", "Wind and solar"],
        series=[Series("Country A", [40, 25, 15, 10, 10]), Series("Country B", [10, 20, 5, 25, 40])],
        y_label="Share of generation",
        unit="%",
        kind="bar",
    ),
    "household-spending": ChartSpec(
        title="Average household spending by category, 2010 and 2020",
        categories=["Housing", "Food", "Transport", "Leisure", "Other"],
        series=[Series("2010", [30, 22, 18, 15, 15]), Series("2020", [38, 18, 14, 18, 12])],
        y_label="Share of spending",
        unit="%",
        kind="bar",
    ),
    "university-enrolment": ChartSpec(
        title="University enrolment by subject area, 2015-2023",
        categories=["2015", "2017", "2019", "2021", "2023"],
        series=[
            Series("Engineering", [12, 14, 17, 21, 26]),
            Series("Humanities", [24, 22, 19, 16, 13]),
            Series("Health sciences", [18, 19, 21, 24, 27]),
        ],
        y_label="Students (thousands)",
        kind="line",
    ),
}

OUT = Path(__file__).resolve().parent.parent / "media" / "charts"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    for name, spec in CHARTS.items():
        svg = render(spec)
        path = OUT / f"{name}.svg"
        status = "exists" if path.exists() else "missing"

        if args.apply:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(svg, encoding="utf-8")
            # The description is written alongside, from the same numbers, so
            # a screen-reader alternative cannot drift from the chart.
            path.with_suffix(".txt").write_text(describe(spec), encoding="utf-8")
            status = "written"

        print(f"  {name:<24} {status:<8} {len(svg):>6} bytes")

    if not args.apply:
        print("\nNothing written. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
