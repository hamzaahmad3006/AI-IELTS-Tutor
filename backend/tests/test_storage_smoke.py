"""Smoke test: object storage and signed URLs.

The signature is the whole security story for a recording of someone's voice.
Without it, /media/<key> is readable by anyone who can guess a key, and a key
guessed once is a key readable forever.

Every assertion here is about a URL that must NOT work: expired, re-signed for a
different object, tampered, or absent.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_storage.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from fastapi.testclient import TestClient  # noqa: E402

from core.config import get_settings  # noqa: E402
from core.storage import (  # noqa: E402
    RECORDINGS_PREFIX,
    LocalStorage,
    StorageError,
    sign,
    verify,
)
from main import app  # noqa: E402

SECRET = "a-storage-signing-secret-long-enough"
AUDIO = b"RIFF" + bytes(2048)


def check_round_trip(root: Path) -> None:
    store = LocalStorage(root=root, secret=SECRET)
    key = f"{RECORDINGS_PREFIX}/user-1/answer-1.m4a"

    assert not store.exists(key)
    store.put(key, AUDIO, content_type="audio/mp4")
    assert store.exists(key)
    assert store.open(key) == AUDIO

    assert store.delete(key) is True
    assert store.delete(key) is False, "deleting twice should report nothing done"
    assert not store.exists(key)

    try:
        store.open(key)
    except StorageError:
        pass
    else:  # pragma: no cover
        raise AssertionError("reading a missing object should raise")


def check_no_partial_objects(root: Path) -> None:
    """A crash mid-write must not leave a truncated object.

    Written to a temp file and moved into place, so a reader sees either the
    whole object or nothing -- never half an audio file that decodes to silence.
    """
    store = LocalStorage(root=root, secret=SECRET)
    key = f"{RECORDINGS_PREFIX}/atomic.m4a"
    store.put(key, AUDIO, content_type="audio/mp4")

    leftovers = list(root.rglob("*.part"))
    assert leftovers == [], leftovers
    assert store.open(key) == AUDIO


def check_traversal_is_refused(root: Path) -> None:
    store = LocalStorage(root=root, secret=SECRET)
    for key in (
        "../../etc/passwd",
        "recordings/../../secrets",
        "/etc/passwd",
        "recordings/./../../x",
        "recordings\\..\\..\\x",
        "",
    ):
        try:
            store.put(key, b"x", content_type="text/plain")
        except StorageError:
            pass
        else:  # pragma: no cover
            raise AssertionError(f"traversal accepted: {key!r}")


def check_signatures() -> None:
    key = f"{RECORDINGS_PREFIX}/user-1/answer.m4a"
    future = int(time.time()) + 600
    signature = sign(key, future, SECRET)

    assert verify(key, future, signature, SECRET)

    # Wrong secret.
    assert not verify(key, future, signature, "another-secret")

    # Expired, correctly signed.
    past = int(time.time()) - 1
    assert not verify(key, past, sign(key, past, SECRET), SECRET)

    # A signature for one object must not admit another. Signing the key and
    # the expiry together is what prevents pairing a valid signature with a
    # later expiry lifted from a different URL.
    other = f"{RECORDINGS_PREFIX}/user-2/answer.m4a"
    assert not verify(other, future, signature, SECRET)

    # Tampered expiry.
    assert not verify(key, future + 3600, signature, SECRET)

    # Tampered signature. The replacement character has to differ from the one
    # it replaces: appending a fixed "0" produces an identical signature
    # whenever the last hex digit is already zero, which is a one-in-sixteen
    # test that passes locally and fails in CI.
    flipped = "1" if signature[-1] == "0" else "0"
    tampered = signature[:-1] + flipped
    assert tampered != signature
    assert not verify(key, future, tampered, SECRET)


def check_signed_url_shape(root: Path) -> None:
    store = LocalStorage(root=root, secret=SECRET)
    key = f"{RECORDINGS_PREFIX}/user-1/answer.m4a"
    url = store.signed_url(key, ttl_seconds=300)

    assert url.path.startswith("/media/")
    assert "expires=" in url.path and "sig=" in url.path
    assert url.expires_at > int(time.time())

    # The secret must never appear in something handed to a client.
    assert SECRET not in url.path


def check_media_route_enforces_signatures() -> None:
    """The rule that actually protects a recording, over HTTP."""
    root = Path(__file__).resolve().parent.parent / "media"
    settings = get_settings()
    store = LocalStorage(root=root, secret=settings.jwt_secret)

    key = f"{RECORDINGS_PREFIX}/smoke/answer.m4a"
    store.put(key, AUDIO, content_type="audio/mp4")

    try:
        with TestClient(app) as client:
            # Unsigned: refused before the file is touched, so an attacker
            # cannot even confirm the key exists.
            assert client.get(f"/media/{key}").status_code == 403

            # Signed but expired.
            past = int(time.time()) - 10
            r = client.get(
                f"/media/{key}",
                params={"expires": past, "sig": sign(key, past, settings.jwt_secret)},
            )
            assert r.status_code == 403, r.text

            # Signature for a different object.
            future = int(time.time()) + 600
            r = client.get(
                f"/media/{key}",
                params={
                    "expires": future,
                    "sig": sign("recordings/other.m4a", future, settings.jwt_secret),
                },
            )
            assert r.status_code == 403, r.text

            # Bad signature and expired link give the same message: telling
            # them apart tells an attacker whether they got the signature right.
            assert "invalid or has expired" in r.text

            # Correctly signed.
            url = store.signed_url(key)
            r = client.get(url.path)
            assert r.status_code == 200, r.text
            assert r.content == AUDIO

            # Public content still needs no signature: seeded clips are the
            # same for every learner, and minting a URL each would buy nothing.
            clips = client.get("/media/seed")
            assert clips.status_code in (404, 400), "a directory should not stream"
    finally:
        store.delete(key)


def check_recording_keys() -> None:
    """Keys line a recording up with the turn it belongs to."""
    from core.storage import extension_for, recording_key

    key = recording_key("sess-1", 0, "m4a")
    assert key.startswith(f"{RECORDINGS_PREFIX}/sess-1/")
    # Zero-padded, so turn 2 and turn 10 sort in the order they were spoken
    # rather than lexicographically.
    assert "turn-000" in key
    assert recording_key("sess-1", 10) > recording_key("sess-1", 2)

    # Re-uploading the same turn overwrites rather than accumulating orphans.
    assert recording_key("sess-1", 3) == recording_key("sess-1", 3)

    # No learner id in the path: session ids are already unguessable, and a
    # user id in a key appears in every log line that mentions the object.
    assert "user" not in key

    assert extension_for("audio/mp4") == "m4a"
    assert extension_for("audio/wav; codecs=1") == "wav"
    # An unknown type still produces a usable key rather than an exception.
    assert extension_for("application/octet-stream") == "m4a"
    assert extension_for("") == "m4a"


def run() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        check_round_trip(Path(tmp))
    with tempfile.TemporaryDirectory() as tmp:
        check_no_partial_objects(Path(tmp))
    with tempfile.TemporaryDirectory() as tmp:
        check_traversal_is_refused(Path(tmp))
    check_signatures()
    check_recording_keys()
    with tempfile.TemporaryDirectory() as tmp:
        check_signed_url_shape(Path(tmp))
    check_media_route_enforces_signatures()

    print("STORAGE SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
