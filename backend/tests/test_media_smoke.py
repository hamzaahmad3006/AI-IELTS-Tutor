"""Smoke test: listening audio is actually served (and traversal is blocked).

The API previously advertised an `audioUrl` that returned 404, so no client
could ever play a clip.
"""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path
import wave

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_media.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


def run() -> None:
    with TestClient(app) as client:
        client.post(
            "/v1/auth/register",
            json={
                "fullName": "Media User",
                "email": "media@example.com",
                "password": "StrongPass123",
            },
        )
        login = client.post(
            "/v1/auth/login",
            json={"email": "media@example.com", "password": "StrongPass123"},
        ).json()
        headers = {"Authorization": f"Bearer {login['tokens']['accessToken']}"}

        clip = client.get("/v1/listening/clips", headers=headers).json()
        audio_url = clip["audioUrl"]
        assert audio_url.startswith("/media/"), audio_url

        # The advertised URL must actually resolve.
        r = client.get(audio_url)
        assert r.status_code == 200, f"{audio_url} -> {r.status_code}"
        assert r.headers["content-type"].startswith("audio/"), r.headers

        # And it must be real, decodable audio - not arbitrary bytes.
        with wave.open(io.BytesIO(r.content)) as handle:
            duration = round(handle.getnframes() / handle.getframerate())
            assert duration > 0, "audio has no frames"
        # Duration should match what the clip metadata advertises.
        assert abs(duration - clip["durationSec"]) <= 1, (
            duration,
            clip["durationSec"],
        )

        # Unknown media is a clean 404, not a server error.
        assert client.get("/media/does/not/exist.wav").status_code == 404

        # Path traversal must never escape the media root.
        for attempt in (
            "/media/../main.py",
            "/media/seed/../../main.py",
            "/media/....//main.py",
        ):
            assert client.get(attempt).status_code in (400, 404), attempt

    print("MEDIA SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
