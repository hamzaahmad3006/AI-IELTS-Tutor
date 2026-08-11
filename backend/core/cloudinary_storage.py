"""Cloudinary object storage.

An adapter for the `ObjectStorage` port, speaking Cloudinary's REST API over
httpx rather than through the `cloudinary` SDK — the same choice the LLM
adapters make, and for the same reason: four verbs and a signature do not
justify a dependency, and this way the request shape is visible in the file
that sends it.

Two things about Cloudinary shape this file, and neither is optional:

**Audio lives under the `video` resource type.** There is no `audio` type.
Uploading an .m4a as `raw` stores the bytes but forfeits everything Cloudinary
is for, and uploading it as `image` fails. The mapping is in `resource_type_for`.

**Delivery is public by default.** An `upload`-type asset is readable by
anyone who can guess its URL. That is fine for seeded listening clips, which
are identical for every learner, and not fine for a recording of someone's
voice. So the split the port already draws — `RECORDINGS_PREFIX` is private,
everything else is public — maps onto Cloudinary's own `authenticated` vs
`upload` delivery types, and private objects are served through expiring
download URLs rather than the CDN.

That last point is the one real difference from a presigned S3 URL. Cloudinary
signs delivery URLs (`s--abc123--/`) to stop tampering, but those signatures do
not expire; a leaked one works forever. The expiring mechanism is the private
download endpoint, whose signature covers an `expires_at`, so that is what
`signed_url` returns for recordings. It is served by the API host rather than
the CDN, which costs caching — and per-learner private audio should not be
sitting in a CDN edge cache anyway.

Signatures here are checked against the official SDK in
tests/test_cloudinary_storage_smoke.py and the vectors pinned, so what ships is
not a guess about the algorithm. What is genuinely untested is the network
round trip: real credentials, account limits, whether the plan permits the
resource type. No local adapter can cover that.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from urllib.parse import quote, urlencode

import httpx

from core.storage import (
    DEFAULT_TTL_SECONDS,
    RECORDINGS_PREFIX,
    SignedUrl,
    StorageError,
    _safe_key,
)

API_BASE = "https://api.cloudinary.com/v1_1"
CDN_BASE = "https://res.cloudinary.com"

#: Cloudinary has no `audio` resource type — audio is handled as `video`.
#: Getting this wrong is not a soft failure: the upload is rejected, or the
#: bytes are stored as an opaque blob with none of the media handling that is
#: the reason to be here at all.
VIDEO_EXTENSIONS = frozenset(
    {"m4a", "mp3", "wav", "ogg", "aac", "flac", "webm", "mp4", "mov"}
)
IMAGE_EXTENSIONS = frozenset({"svg", "png", "jpg", "jpeg", "gif", "webp"})


def resource_type_for(key: str) -> str:
    """Which of Cloudinary's three resource types a key belongs to."""
    extension = key.rsplit(".", 1)[-1].lower() if "." in key else ""
    if extension in VIDEO_EXTENSIONS:
        return "video"
    if extension in IMAGE_EXTENSIONS:
        return "image"
    # Everything else — the screen-reader .txt alternatives beside each chart,
    # anything future. `raw` stores bytes verbatim.
    return "raw"


def is_private(key: str) -> bool:
    """Whether this object is somebody's voice rather than shared content."""
    return _safe_key(key).startswith(f"{RECORDINGS_PREFIX}/")


def split_public_id(key: str) -> tuple[str, str]:
    """Split a storage key into Cloudinary's (public_id, format).

    Cloudinary models `image` and `video` assets as an id plus a format, and
    reattaches the extension on delivery — so a public_id carrying its own
    `.m4a` produces `turn-001.m4a.m4a`. `raw` is the opposite: it stores the
    filename verbatim and appends nothing.

    Returning both, and letting the caller decide, is what keeps a key
    round-tripping through `put` and `open` unchanged.
    """
    safe = _safe_key(key)
    if resource_type_for(safe) == "raw" or "." not in safe.rsplit("/", 1)[-1]:
        return safe, ""
    public_id, extension = safe.rsplit(".", 1)
    return public_id, extension


def string_to_sign(params: dict[str, object]) -> str:
    """Cloudinary's canonical string for a request signature.

    Three details, each of which silently produces a wrong signature rather
    than an error:

      - falsy values are omitted entirely, so `overwrite=False` is not signed
        as "false" — it is not signed at all;
      - booleans that *are* included render lowercase;
      - each `key=value` has its `&` percent-encoded before joining, which is
        what stops a value containing `&` from smuggling in another parameter.

    Sorting happens after encoding, on the encoded strings.
    """
    parts: list[str] = []
    for name, value in params.items():
        if not value:
            continue
        if isinstance(value, bool):
            rendered = str(value).lower()
        elif isinstance(value, (list, tuple)):
            rendered = ",".join(str(item) for item in value)
        else:
            rendered = str(value)
        parts.append(f"{name}={rendered}".replace("&", "%26"))
    return "&".join(sorted(parts))


def sign(params: dict[str, object], api_secret: str) -> str:
    return hashlib.sha1(
        (string_to_sign(params) + api_secret).encode("utf-8")
    ).hexdigest()


@dataclass
class CloudinaryStorage:
    """Objects in a Cloudinary account."""

    cloud_name: str
    api_key: str
    api_secret: str
    #: Prefixed to every key, so one account can host several environments
    #: without staging deletions reaching production objects.
    folder: str = ""
    timeout_s: float = 30.0

    name: str = field(default="cloudinary", init=False)

    def __post_init__(self) -> None:
        for label, value in (
            ("cloud name", self.cloud_name),
            ("API key", self.api_key),
            ("API secret", self.api_secret),
        ):
            if not value:
                raise ValueError(f"Cloudinary storage requires a {label}")
        self.folder = self.folder.strip("/")

    # -- addressing ---------------------------------------------------------

    def _scoped(self, key: str) -> str:
        safe = _safe_key(key)
        return f"{self.folder}/{safe}" if self.folder else safe

    def _delivery_type(self, key: str) -> str:
        return "authenticated" if is_private(key) else "upload"

    def _api_url(self, key: str, action: str) -> str:
        return f"{API_BASE}/{self.cloud_name}/{resource_type_for(key)}/{action}"

    def public_url(self, key: str) -> str:
        """The plain CDN URL. Only meaningful for public objects."""
        public_id, extension = split_public_id(self._scoped(key))
        suffix = f".{extension}" if extension else ""
        return (
            f"{CDN_BASE}/{self.cloud_name}/{resource_type_for(key)}"
            f"/{self._delivery_type(key)}/{quote(public_id)}{suffix}"
        )

    # -- signing ------------------------------------------------------------

    def _signed_params(self, params: dict[str, object]) -> dict[str, object]:
        """Attach a timestamp, signature and API key.

        `api_key` is added after signing on purpose — it is not part of the
        signed string, and including it produces a signature the server will
        reject.
        """
        params = {"timestamp": int(time.time()), **params}
        return {
            **params,
            "signature": sign(params, self.api_secret),
            "api_key": self.api_key,
        }

    def download_url(
        self,
        key: str,
        *,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        now: int | None = None,
    ) -> SignedUrl:
        """A URL that grants one object until it expires.

        Cloudinary's signed *delivery* URLs authenticate but never expire, so
        this uses the private download endpoint instead, whose signature covers
        `expires_at`. A leaked link therefore stops working, which is the whole
        point of signing a recording of someone's voice.
        """
        scoped = self._scoped(key)
        public_id, extension = split_public_id(scoped)
        issued = now if now is not None else int(time.time())
        expires_at = issued + ttl_seconds

        params: dict[str, object] = {
            "timestamp": issued,
            "public_id": public_id,
            "format": extension,
            "type": self._delivery_type(key),
            "expires_at": expires_at,
        }
        signed = {
            **params,
            "signature": sign(params, self.api_secret),
            "api_key": self.api_key,
        }
        return SignedUrl(
            path=f"{self._api_url(key, 'download')}?{urlencode(signed)}",
            expires_at=expires_at,
        )

    # -- ObjectStorage ------------------------------------------------------

    def put(self, key: str, data: bytes, *, content_type: str) -> str:
        scoped = self._scoped(key)
        public_id, _ = split_public_id(scoped)
        params = self._signed_params(
            {
                "public_id": public_id,
                "type": self._delivery_type(key),
                # Re-uploading the same turn must replace it. Without this
                # Cloudinary keeps the original and the learner hears their
                # previous attempt.
                "overwrite": True,
                # Purge the CDN edge copy too, or the old audio survives the
                # overwrite for as long as the cache holds it.
                "invalidate": True,
            }
        )
        with httpx.Client(timeout=self.timeout_s) as client:
            response = client.post(
                self._api_url(key, "upload"),
                data={k: str(v) for k, v in params.items()},
                files={"file": (public_id, data, content_type or "application/octet-stream")},
            )
        if response.status_code >= 300:
            raise StorageError(_describe(response, key))
        return key

    def open(self, key: str) -> bytes:
        url = (
            self.download_url(key).path
            if is_private(key)
            else self.public_url(key)
        )
        with httpx.Client(timeout=self.timeout_s, follow_redirects=True) as client:
            response = client.get(url)
        if response.status_code == 404:
            raise StorageError(f"No such object: {key}")
        if response.status_code >= 300:
            raise StorageError(_describe(response, key))
        return response.content

    def exists(self, key: str) -> bool:
        try:
            url = (
                self.download_url(key).path
                if is_private(key)
                else self.public_url(key)
            )
        except StorageError:
            # An unsafe key cannot exist; callers use this as a guard and
            # should not have to catch for that.
            return False
        with httpx.Client(timeout=self.timeout_s, follow_redirects=True) as client:
            response = client.head(url)
        return response.status_code == 200

    def delete(self, key: str) -> bool:
        scoped = self._scoped(key)
        public_id, _ = split_public_id(scoped)
        params = self._signed_params(
            {
                "public_id": public_id,
                "type": self._delivery_type(key),
                "invalidate": True,
            }
        )
        with httpx.Client(timeout=self.timeout_s) as client:
            response = client.post(
                self._api_url(key, "destroy"),
                data={k: str(v) for k, v in params.items()},
            )
        if response.status_code >= 300:
            raise StorageError(_describe(response, key))
        # A destroy for something that was never there is a 200 with
        # {"result": "not found"}. Reported as False to match LocalStorage,
        # which the retention job relies on for its counts.
        try:
            result = response.json().get("result")
        except ValueError:
            result = None
        return result == "ok"

    def signed_url(
        self, key: str, *, ttl_seconds: int = DEFAULT_TTL_SECONDS
    ) -> SignedUrl:
        if not is_private(key):
            # Shared content, identical for every learner. Minting a
            # per-learner expiring URL for it would buy nothing and cost the
            # CDN cache.
            return SignedUrl(
                path=self.public_url(key),
                expires_at=int(time.time()) + ttl_seconds,
            )
        return self.download_url(key, ttl_seconds=ttl_seconds)


def _describe(response: httpx.Response, key: str) -> str:
    """A message that says what went wrong, not just that it did.

    Cloudinary returns its reason as JSON `{"error": {"message": ...}}`.
    Without pulling that out an operator sees "401" and cannot tell a bad
    signature from an unsigned upload preset from a plan that does not allow
    the resource type.
    """
    message = ""
    try:
        payload = response.json()
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                message = str(error.get("message") or "")
            elif error:
                message = str(error)
    except (ValueError, json.JSONDecodeError):
        message = (response.text or "")[:200]
    return f"Cloudinary {response.status_code} {message or 'error'} for {key}".strip()
