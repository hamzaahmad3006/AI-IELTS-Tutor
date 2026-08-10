"""Smoke test: Task 1 chart rendering.

A chart drawn from mismatched or mis-scaled data is worse than no chart: the
candidate describes what they see, and if what they see is wrong they are
marked down for our bug.

The SVG is parsed rather than string-matched, so these assert the document is
actually well formed and the geometry is inside the canvas.
"""

from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_charts.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from core.charts import (  # noqa: E402
    HEIGHT,
    SERIES_COLOURS,
    SERIES_DASHES,
    WIDTH,
    ChartSpec,
    Series,
    describe,
    render,
)

TRANSPORT = ChartSpec(
    title="Transport use in one city, 2000-2020",
    categories=["2000", "2005", "2010", "2015", "2020"],
    series=[
        Series("Bus", [45, 40, 35, 30, 25]),
        Series("Car", [30, 35, 40, 45, 50]),
        Series("Bicycle", [10, 12, 15, 18, 20]),
    ],
    y_label="Share of residents",
    unit="%",
    kind="line",
)


def check_document_is_well_formed() -> None:
    svg = render(TRANSPORT)
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    assert root.get("viewBox") == f"0 0 {WIDTH} {HEIGHT}"

    # Labelled for a screen reader. A chart with no accessible name is an
    # unlabelled image in the middle of the question.
    assert root.get("role") == "img"
    assert root.get("aria-label")


def check_geometry_stays_on_the_canvas() -> None:
    """Points outside the viewBox are invisible, and silently so."""
    svg = render(TRANSPORT)
    root = ET.fromstring(svg)

    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1]
        if tag == "polyline":
            for pair in (element.get("points") or "").split():
                x, y = (float(n) for n in pair.split(","))
                assert 0 <= x <= WIDTH, x
                assert 0 <= y <= HEIGHT, y
        if tag == "circle":
            assert 0 <= float(element.get("cx") or 0) <= WIDTH
            assert 0 <= float(element.get("cy") or 0) <= HEIGHT
        if tag == "rect" and element.get("fill") != "#ffffff":
            assert float(element.get("height") or 0) >= 0, "negative bar height"


def check_bars_are_proportional() -> None:
    """Twice the value must be twice the bar. Otherwise the chart lies."""
    spec = ChartSpec(
        title="Comparison",
        categories=["A"],
        series=[Series("One", [25]), Series("Two", [50])],
        kind="bar",
    )
    root = ET.fromstring(render(spec))
    # Legend swatches are rects too, and sit below the plot. Filtering by the
    # plot area rather than by size, since a small bar is still a bar.
    bars = sorted(
        float(el.get("height") or 0)
        for el in root.iter()
        if el.tag.rsplit("}", 1)[-1] == "rect"
        and el.get("fill") != "#ffffff"
        and float(el.get("y") or 0) < HEIGHT - 40
    )
    assert len(bars) >= 2, bars
    assert abs(bars[1] / bars[0] - 2.0) < 0.05, bars


def check_series_are_distinguishable_without_colour() -> None:
    """A chart told apart only by hue excludes the candidates least able to say so."""
    svg = render(TRANSPORT)
    # Three series, three different dash patterns among the first three.
    assert len(set(SERIES_DASHES[:3])) == 3
    assert len(set(SERIES_COLOURS[:3])) == 3
    assert "stroke-dasharray" in svg


def check_axis_lands_on_readable_numbers() -> None:
    """Candidates quote figures off the gridlines, so gridlines must be quotable."""
    spec = ChartSpec(
        title="Odd maximum",
        categories=["A", "B"],
        series=[Series("X", [3.0, 63.7])],
        unit="%",
    )
    svg = render(spec)
    # 63.7 rounds up to 100, so the labels are 0/20/40/60/80/100 rather than
    # 0/12.74/25.48/...
    assert ">100%<" in svg
    assert "63.7" not in svg


def check_single_series_has_no_legend() -> None:
    spec = ChartSpec(
        title="One line",
        categories=["A", "B"],
        series=[Series("Only", [1, 2])],
    )
    svg = render(spec)
    # A legend explaining one line is furniture that explains nothing.
    assert "Only" not in svg


def check_titles_are_escaped() -> None:
    """A title is data. Unescaped, it breaks the document or injects markup."""
    spec = ChartSpec(
        title='Growth <b>&</b> "decline"',
        categories=["A"],
        series=[Series("X", [1])],
    )
    svg = render(spec)
    ET.fromstring(svg)  # would raise if the markup were broken
    assert "<b>" not in svg


def check_mismatched_data_is_refused() -> None:
    """A chart drawn from mismatched data is one the candidate cannot describe."""
    for spec in (
        ChartSpec(title="t", categories=["A", "B"], series=[Series("X", [1])]),
        ChartSpec(title="t", categories=[], series=[Series("X", [1])]),
        ChartSpec(title="t", categories=["A"], series=[]),
        ChartSpec(title="t", categories=["A"], series=[Series("X", [1])], kind="pie"),
    ):
        try:
            render(spec)
        except ValueError:
            pass
        else:  # pragma: no cover
            raise AssertionError(f"accepted bad spec: {spec.title}/{spec.kind}")


def check_description_matches_the_chart() -> None:
    """The accessible alternative is generated from the same numbers.

    Written by hand it would drift from the chart, and a screen-reader user
    would be describing different data from everyone else.
    """
    text = describe(TRANSPORT)
    assert "Bus" in text and "Car" in text and "Bicycle" in text
    for value in ("45%", "25%", "50%", "20%"):
        assert value in text, value
    assert "2000" in text and "2020" in text


def check_assets_are_served() -> None:
    """The generated charts reach a learner as images, not downloads."""
    from fastapi.testclient import TestClient

    from main import app

    password = "StrongPass123"
    with TestClient(app) as client:
        token = client.post(
            "/v1/auth/register",
            json={
                "fullName": "Chart Learner",
                "email": "charts@example.com",
                "password": password,
            },
        ).json()["tokens"]["accessToken"]
        headers = {"Authorization": f"Bearer {token}"}
        client.post(
            "/v1/onboarding",
            headers=headers,
            json={
                "examType": "academic",
                "selfLevel": "intermediate",
                "targetBand": 7.0,
                "examDate": None,
                "dailyMinutes": 30,
                "consentVoice": True,
                "consentAi": True,
            },
        )

        refs = set()
        for _ in range(30):
            body = client.get(
                "/v1/writing/prompts",
                headers=headers,
                params={"taskNumber": 1, "examType": "academic"},
            ).json()
            if body.get("assetRef"):
                refs.add(body["assetRef"])

        assert refs, "no chart-backed Task 1 prompt was ever served"

        for ref in sorted(refs):
            image = client.get(f"/media/{ref}")
            assert image.status_code == 200, ref
            # image/svg+xml, not the octet-stream fallback, which a client
            # downloads instead of rendering.
            assert image.headers["content-type"].startswith("image/svg+xml"), ref
            ET.fromstring(image.content)

            alt = client.get(f"/media/{ref.replace('.svg', '.txt')}")
            # The screen-reader alternative ships beside every chart. Without
            # it the question is an unlabelled image.
            assert alt.status_code == 200, ref
            assert alt.text.strip()


def run() -> None:
    check_document_is_well_formed()
    check_geometry_stays_on_the_canvas()
    check_bars_are_proportional()
    check_series_are_distinguishable_without_colour()
    check_axis_lands_on_readable_numbers()
    check_single_series_has_no_legend()
    check_titles_are_escaped()
    check_mismatched_data_is_refused()
    check_description_matches_the_chart()
    check_assets_are_served()

    print("CHARTS SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
