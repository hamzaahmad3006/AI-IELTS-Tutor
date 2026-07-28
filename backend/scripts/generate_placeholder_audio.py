"""Generate placeholder audio for the seeded listening clips.

These are SILENT files whose only purpose is to make the media pipeline work
end to end (the clip URL resolves and a player can load it). They must be
replaced with real spoken recordings before launch — the questions reference
content a learner is supposed to hear.

Usage:  python scripts/generate_placeholder_audio.py
"""

from __future__ import annotations

import pathlib
import wave

# Durations must match the `duration_sec` seeded in listening_controller.py.
CLIPS = {
    "orientation.wav": 45,
    "museum.wav": 48,
    "booking.wav": 52,
}

# Low fidelity on purpose: these are silent placeholders, so keep them small.
SAMPLE_RATE = 8000
SAMPLE_WIDTH = 1  # 8-bit
OUTPUT_DIR = pathlib.Path(__file__).resolve().parent.parent / "media" / "seed" / "audio"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, seconds in CLIPS.items():
        path = OUTPUT_DIR / name
        with wave.open(str(path), "w") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(SAMPLE_WIDTH)
            handle.setframerate(SAMPLE_RATE)
            # 8-bit PCM silence is 0x80 (unsigned midpoint), not 0x00.
            handle.writeframes(b"\x80" * SAMPLE_RATE * seconds)
        print(f"{name}: {path.stat().st_size / 1024:.0f} KB ({seconds}s)")


if __name__ == "__main__":
    main()
