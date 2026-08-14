"""Starts an examiner worker for a room, and keeps track of it.

The worker runs as its own process (see `voice.live_worker` for why). Something
has to launch it, and the natural moment is when the client asks for a room
token -- that is the one point where we know a candidate is about to join.

Deliberately small. This is not a job queue: it spawns a process, remembers it,
and refuses to spawn a second one for the same room. A real deployment would
put the workers behind a scheduler with health checks and backpressure, and
that is a different piece of work from making one interview happen.

Spawn failures are logged, never raised. The token is still valid without a
worker -- the candidate joins a room where nobody talks back, which is a bad
interview but a working app, and is far better than a 500 on the endpoint that
was supposed to start their exam.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger("voice.supervisor")

BACKEND_ROOT = Path(__file__).resolve().parent.parent

#: room name -> process. Per-process state, which is the honest scope: with
#: several API instances each keeps its own view, and the guard below stops
#: duplicates only within one. Two instances could both spawn a worker for the
#: same room; the second would find the room occupied and the examiner would be
#: heard twice. Fine for one API process, which is what a demo and a laptop
#: both are.
_running: dict[str, subprocess.Popen] = {}


def is_running(room: str) -> bool:
    process = _running.get(room)
    if process is None:
        return False
    if process.poll() is not None:
        # Finished or crashed. Dropped so the next request can start a fresh
        # one rather than assuming this room is served.
        _running.pop(room, None)
        return False
    return True


def ensure_worker(room: str) -> bool:
    """Start an examiner for `room` unless one is already running.

    Returns whether a worker is now believed to be running.
    """
    if is_running(room):
        logger.info("worker already running", extra={"room": room})
        return True

    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "voice.live_worker", "--room", room],
            cwd=str(BACKEND_ROOT),
            # Inherited so the worker gets the same .env-derived config the API
            # is using. Passing a curated subset would drift the moment someone
            # adds a setting.
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:  # noqa: BLE001 - see module docstring
        logger.exception("could not start examiner worker", extra={"room": room})
        return False

    _running[room] = process
    logger.info("examiner worker started", extra={"room": room, "pid": process.pid})
    return True


def stop_worker(room: str) -> None:
    """End the worker for a room, if one is running."""
    process = _running.pop(room, None)
    if process is None or process.poll() is not None:
        return
    process.terminate()
    logger.info("examiner worker stopped", extra={"room": room})
