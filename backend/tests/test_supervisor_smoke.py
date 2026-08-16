"""Smoke test: the examiner worker supervisor.

Small module, but its two failure modes are both silent.

If a finished worker is never forgotten, the room it served is remembered as
occupied forever, and the next candidate joins to an examiner that is not
there -- a connected room, a published microphone, and nobody talking.

If a duplicate is spawned, two examiners join the same room and both greet the
candidate, on top of each other.

`subprocess.Popen` is patched throughout: this decides *whether* to spawn, and
that decision is testable without actually starting Python processes.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_supervisor.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from voice import supervisor  # noqa: E402


class FakeProcess:
    """Stands in for Popen. `code` None means still running."""

    def __init__(self, pid: int = 4242, code: int | None = None) -> None:
        self.pid = pid
        self._code = code
        self.terminated = False

    def poll(self) -> int | None:
        return self._code

    def terminate(self) -> None:
        self.terminated = True
        self._code = -15

    def finish(self, code: int = 0) -> None:
        self._code = code


def _patch(spawned: list[list[str]], process: FakeProcess | None = None):
    """Replace Popen, recording the command it was asked to run."""

    def fake_popen(command, **_kwargs):
        spawned.append(list(command))
        return process or FakeProcess()

    original = supervisor.subprocess.Popen
    supervisor.subprocess.Popen = fake_popen  # type: ignore[assignment]
    return original


def _reset() -> None:
    supervisor._running.clear()


def check_spawns_once_per_room() -> None:
    spawned: list[list[str]] = []
    original = _patch(spawned)
    try:
        _reset()
        assert supervisor.ensure_worker("room-a") is True
        assert len(spawned) == 1

        # Two examiners in one room both greet the candidate, over each other.
        assert supervisor.ensure_worker("room-a") is True
        assert len(spawned) == 1, "a duplicate worker was spawned"

        # A different room is a different interview.
        assert supervisor.ensure_worker("room-b") is True
        assert len(spawned) == 2
    finally:
        supervisor.subprocess.Popen = original  # type: ignore[assignment]
        _reset()


def check_the_command_is_the_worker() -> None:
    """Room name and module have to survive intact or the worker joins nothing."""
    spawned: list[list[str]] = []
    original = _patch(spawned)
    try:
        _reset()
        supervisor.ensure_worker("interview-abc123")
        command = spawned[0]

        assert command[0] == sys.executable
        assert command[1:3] == ["-m", "voice.live_worker"]
        assert "--room" in command
        assert command[command.index("--room") + 1] == "interview-abc123"
    finally:
        supervisor.subprocess.Popen = original  # type: ignore[assignment]
        _reset()


def check_a_finished_worker_is_forgotten() -> None:
    """Otherwise the room is remembered as served and never gets an examiner."""
    process = FakeProcess()
    spawned: list[list[str]] = []
    original = _patch(spawned, process)
    try:
        _reset()
        supervisor.ensure_worker("room-c")
        assert supervisor.is_running("room-c") is True

        # The interview ended, or the worker crashed.
        process.finish()
        assert supervisor.is_running("room-c") is False
        assert "room-c" not in supervisor._running, "the dead process was kept"

        # And the next request starts a fresh one rather than assuming the
        # room is still served.
        supervisor.ensure_worker("room-c")
        assert len(spawned) == 2
    finally:
        supervisor.subprocess.Popen = original  # type: ignore[assignment]
        _reset()


def check_a_spawn_failure_is_reported_not_raised() -> None:
    """The token is still valid without a worker.

    A silent room is a bad interview; a 500 on the request that was meant to
    start the exam is a broken app.
    """

    def exploding_popen(command, **_kwargs):
        raise OSError("no such executable")

    original = supervisor.subprocess.Popen
    supervisor.subprocess.Popen = exploding_popen  # type: ignore[assignment]
    try:
        _reset()
        assert supervisor.ensure_worker("room-d") is False
        assert supervisor.is_running("room-d") is False
    finally:
        supervisor.subprocess.Popen = original  # type: ignore[assignment]
        _reset()


def check_stop_is_safe_to_call_twice() -> None:
    process = FakeProcess()
    spawned: list[list[str]] = []
    original = _patch(spawned, process)
    try:
        _reset()
        supervisor.ensure_worker("room-e")

        supervisor.stop_worker("room-e")
        assert process.terminated is True
        assert supervisor.is_running("room-e") is False

        # Idempotent, and safe for a room that never had one -- it runs from
        # cleanup paths where raising would mask the real failure.
        supervisor.stop_worker("room-e")
        supervisor.stop_worker("never-existed")
    finally:
        supervisor.subprocess.Popen = original  # type: ignore[assignment]
        _reset()


def check_unknown_room_is_not_running() -> None:
    _reset()
    assert supervisor.is_running("nothing-here") is False


def run() -> None:
    check_spawns_once_per_room()
    check_the_command_is_the_worker()
    check_a_finished_worker_is_forgotten()
    check_a_spawn_failure_is_reported_not_raised()
    check_stop_is_safe_to_call_twice()
    check_unknown_room_is_not_running()

    print("SUPERVISOR SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
