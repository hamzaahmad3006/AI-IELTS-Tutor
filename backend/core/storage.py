"""Object storage, with signed URLs.

`AudioClip.object_key` has always been a storage key rather than a path, and the
media route has always resolved it against a directory. This makes that
resolution a port, so a hosted backend is an adapter rather than a rewrite, and
adds the piece that was missing either way: signatures.

Without a signature, `/media/<key>` is world-readable to anyone who can guess a
key. That is tolerable for seeded listening clips, which are the same for
everybody, and not tolerable for a recording of someone's voice.

The signature is an HMAC over the key and an expiry, so a URL is valid for one
object for a limited time and cannot be edited into a URL for another. It is
verified without a database lookup, which is what lets audio be served by a
plain file handler rather than an authenticated endpoint.

Local storage is the default because it needs nothing. `core/cloudinary_storage`
is the hosted adapter, selected with STORAGE_BACKEND=cloudinary.

An earlier draft of this note said a storage adapter that cannot be run against
a real account is a guess. That was right about the risk and wrong about where
it sits: what fails silently is the request signature, and signatures are
exactly what can be checked without an account. The Cloudinary adapter's are
verified against the vendor's own SDK. The genuinely untested part is the
network round trip, which is a narrower and more honest gap.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable
from urllib.parse import quote, urlencode

#: Long enough to start playback on a slow connection, short enough that a
#: leaked URL is worthless by the time it is shared.
DEFAULT_TTL_SECONDS = 15 * 60

#: Objects under this prefix are private and require a signature. Everything
#: else -- seeded listening clips, identical for every learner -- is public,
#: because minting a URL per clip per learner for shared content buys nothing.
RECORDINGS_PREFIX = "recordings"

#: Largest recording accepted from a client. Roughly forty minutes of the AAC
#: the phone records at, so it bounds abuse without ever refusing a real answer.
#:
#: Lives here rather than in a controller because two upload paths enforce it
#: -- the interview turn and the practice answer -- and the frontend refuses
#: above the same number before spending a phone's data on the attempt. Three
#: copies that can drift apart means a recording the app accepts and the API
#: rejects, after the upload.
MAX_AUDIO_BYTES = 10 * 1024 * 1024


class StorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class SignedUrl:
    path: str
    expires_at: int

    def __str__(self) -> str:
        return self.path


@runtime_checkable
class ObjectStorage(Protocol):
    """Somewhere to put bytes and get them back."""

    name: str

    def put(self, key: str, data: bytes, *, content_type: str) -> str: ...

    def open(self, key: str) -> bytes: ...

    def exists(self, key: str) -> bool: ...

    def delete(self, key: str) -> bool: ...

    def signed_url(self, key: str, *, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> SignedUrl: ...


def _safe_key(key: str) -> str:
    """Reject anything that could escape the storage root.

    Checked on the key rather than on the resolved path, so a traversal is
    refused before it touches the filesystem at all. The media route also
    resolves and compares; two checks because this one is cheap and the
    consequence of missing it is reading arbitrary files off the server.
    """
    if not key or key.startswith("/") or "\\" in key:
        raise StorageError(f"Invalid object key: {key!r}")
    parts = [p for p in key.split("/") if p]
    if any(p in ("..", ".") for p in parts):
        raise StorageError(f"Invalid object key: {key!r}")
    return "/".join(parts)


def sign(key: str, expires_at: int, secret: str) -> str:
    """HMAC over the key and expiry together.

    Together, not separately: signing them independently would let someone
    take a valid signature for one key and pair it with a later expiry from
    another URL.
    """
    message = f"{key}\n{expires_at}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def verify(key: str, expires_at: int, signature: str, secret: str) -> bool:
    """Whether this signature admits this key right now."""
    if expires_at < int(time.time()):
        return False
    expected = sign(key, expires_at, secret)
    # Constant-time: a timing difference here would let a signature be guessed
    # a byte at a time.
    return hmac.compare_digest(expected, signature)


@dataclass
class LocalStorage:
    """Files under a directory, with signed URLs served by the media route."""

    root: Path
    secret: str
    #: URL prefix the signed path is built from.
    base_path: str = "/media"

    name: str = "local"

    def _path(self, key: str) -> Path:
        return self.root / _safe_key(key)

    def put(self, key: str, data: bytes, *, content_type: str) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Written to a temp file and moved into place, so a crash mid-write
        # cannot leave a truncated object that later reads treat as complete.
        tmp = path.with_suffix(path.suffix + ".part")
        tmp.write_bytes(data)
        tmp.replace(path)
        return key

    def open(self, key: str) -> bytes:
        path = self._path(key)
        if not path.is_file():
            raise StorageError(f"No such object: {key}")
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        try:
            return self._path(key).is_file()
        except StorageError:
            return False

    def delete(self, key: str) -> bool:
        path = self._path(key)
        if not path.is_file():
            return False
        path.unlink()
        return True

    def signed_url(
        self, key: str, *, ttl_seconds: int = DEFAULT_TTL_SECONDS
    ) -> SignedUrl:
        safe = _safe_key(key)
        expires_at = int(time.time()) + ttl_seconds
        query = urlencode(
            {"expires": expires_at, "sig": sign(safe, expires_at, self.secret)}
        )
        return SignedUrl(
            path=f"{self.base_path}/{quote(safe)}?{query}", expires_at=expires_at
        )


def build_storage(*, root: Path, secret: str) -> ObjectStorage:
    """Pick the storage backend from configuration.

    Local unless Cloudinary is both selected and fully configured. Falling
    back rather than raising on a half-filled config is deliberate: a missing
    cloud name should not take down an app that works perfectly well off local
    disk, and the backend in use is visible as `.name` wherever it matters.
    """
    # Imported here rather than at module scope: cloudinary_storage imports
    # from this module, and at module scope that is a cycle.
    from core.config import get_settings

    settings = get_settings()
    if (settings.storage_backend or "").strip().lower() == "cloudinary":
        if (
            settings.cloudinary_cloud_name
            and settings.cloudinary_api_key
            and settings.cloudinary_api_secret
        ):
            from core.cloudinary_storage import CloudinaryStorage

            return CloudinaryStorage(
                cloud_name=settings.cloudinary_cloud_name,
                api_key=settings.cloudinary_api_key,
                api_secret=settings.cloudinary_api_secret,
                folder=settings.cloudinary_folder,
            )

    return LocalStorage(root=root, secret=secret)


def recording_key(session_id: str, turn_index: int, extension: str = "m4a") -> str:
    """Where one answer's audio lives.

    Keyed by session and turn rather than by a random id, so a recording can be
    found from the transcript it belongs to without a lookup table -- and so
    re-uploading the same turn overwrites rather than accumulating orphans.

    The learner id is deliberately absent: session ids are already unguessable,
    and putting a user id in a path means it appears in every log line that
    mentions the object.
    """
    return f"{RECORDINGS_PREFIX}/{session_id}/turn-{turn_index:03d}.{extension}"


def extension_for(mime_type: str) -> str:
    """File extension for a recording, for the media route's content type."""
    return {
        "audio/mp4": "m4a",
        "audio/m4a": "m4a",
        "audio/mpeg": "mp3",
        "audio/wav": "wav",
        "audio/x-wav": "wav",
        "audio/ogg": "ogg",
    }.get((mime_type or "").split(";")[0].strip().lower(), "m4a")
