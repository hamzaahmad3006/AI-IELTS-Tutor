"""Smoke test: the Cloudinary storage adapter.

Every signature below was produced by the official `cloudinary` SDK
(`api_sign_request`, `api_string_to_sign`, `private_download_url`) and then
pinned here, so CI does not need the SDK to check one hash. If this adapter's
signing drifts, these stop matching.

Regenerate them with the SDK installed:

    import cloudinary.utils as u
    u.now = lambda: 1700000000            # freeze its clock
    u.api_sign_request(params, SECRET)

The signing rules are the interesting part, because each of their edge cases
fails *silently* -- a wrong signature is a 401 that reads like bad credentials
rather than a bug in the string you built. Falsy parameters are dropped rather
than rendered, booleans render lowercase, and `&` inside a value is encoded so
it cannot smuggle in another parameter.

What is genuinely untested is the network round trip: real credentials,
account limits, whether the plan permits the resource type. No local adapter
can cover that, and the backlog says so rather than implying otherwise.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_cloudinary.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

import httpx  # noqa: E402

from core.cloudinary_storage import (  # noqa: E402
    CloudinaryStorage,
    is_private,
    resource_type_for,
    sign,
    split_public_id,
    string_to_sign,
)
from core.storage import ObjectStorage, StorageError  # noqa: E402

CLOUD = "demo-cloud"
API_KEY = "123456789012345"
API_SECRET = "abcd1234SECRETxyz"
NOW = 1700000000
TTL = 900

#: (params, expected string-to-sign, expected signature) — from the SDK.
SIGN_VECTORS = [
    (
        {
            "timestamp": NOW,
            "public_id": "recordings/s1/turn-001",
            "type": "authenticated",
            "overwrite": True,
            "invalidate": True,
        },
        "invalidate=true&overwrite=true&public_id=recordings/s1/turn-001"
        "&timestamp=1700000000&type=authenticated",
        "8111f698fccf963c0bcdd2ac2c3ea6c86d7ac655",
    ),
    (
        {
            "timestamp": NOW,
            "public_id": "clips/listening/part1",
            "type": "upload",
            "format": "wav",
            "expires_at": NOW + 3600,
        },
        "expires_at=1700003600&format=wav&public_id=clips/listening/part1"
        "&timestamp=1700000000&type=upload",
        "79b1a50a2c8015e184faec978376374e037e1149",
    ),
    # Falsy values are dropped entirely rather than rendered. `overwrite=False`
    # signed as "false" is a different signature and a 401 that looks like bad
    # credentials.
    (
        {
            "timestamp": NOW,
            "public_id": "a/b",
            "overwrite": False,
            "attachment": None,
            "format": "",
        },
        "public_id=a/b&timestamp=1700000000",
        "9736ad6aea8d4444ba4fdd2012aaa3f3e6c72937",
    ),
    # An `&` inside a value is encoded before joining, so it cannot be read as
    # a parameter separator and smuggle in another parameter.
    (
        {"timestamp": NOW, "public_id": "weird&name=x", "type": "upload"},
        "public_id=weird%26name=x&timestamp=1700000000&type=upload",
        "80c4e0690f8467529bdc2d2583fc3d45f056d194",
    ),
]

#: (key, expected private-download signature) — from the SDK.
DOWNLOAD_VECTORS = [
    ("recordings/sess-1/turn-003.m4a", "624fed4390b13b1e91532e1bac6702d38cb04f48"),
    ("recordings/s/turn-001.wav", "f4955e8a5fc89c06a5e05f8afe5e87f7722d92c0"),
]


def _storage(**overrides) -> CloudinaryStorage:
    return CloudinaryStorage(
        cloud_name=CLOUD, api_key=API_KEY, api_secret=API_SECRET, **overrides
    )


def check_signatures_match_the_sdk() -> None:
    for params, expected_string, expected_signature in SIGN_VECTORS:
        assert string_to_sign(params) == expected_string, params
        assert sign(params, API_SECRET) == expected_signature, params


def check_download_urls_match_the_sdk() -> None:
    storage = _storage()
    for key, expected in DOWNLOAD_VECTORS:
        url = storage.download_url(key, ttl_seconds=TTL, now=NOW)
        query = parse_qs(urlparse(url.path).query)
        assert query["signature"][0] == expected, key
        # The API key rides along but is deliberately not part of the signed
        # string; signing it produces a signature the server rejects.
        assert query["api_key"][0] == API_KEY
        assert query["expires_at"][0] == str(NOW + TTL)
        assert url.expires_at == NOW + TTL
        # The secret must never appear in a URL that gets logged or shared.
        assert API_SECRET not in url.path


def check_audio_is_a_video_resource() -> None:
    """Cloudinary has no `audio` type, and guessing wrong is not a soft fail."""
    for key in ("a/x.m4a", "a/x.mp3", "a/x.wav", "a/x.ogg", "a/x.aac"):
        assert resource_type_for(key) == "video", key
    for key in ("charts/task1.svg", "a/x.png"):
        assert resource_type_for(key) == "image", key
    # The screen-reader alternatives beside each chart, and anything with no
    # extension at all.
    for key in ("charts/task1.txt", "a/no-extension"):
        assert resource_type_for(key) == "raw", key


def check_keys_round_trip() -> None:
    """A key must survive `put` and come back out of `open` unchanged.

    Cloudinary reattaches the format on delivery for image and video assets,
    so a public_id that kept its own extension yields `turn-001.m4a.m4a`. Raw
    is the opposite and stores the filename verbatim.
    """
    assert split_public_id("recordings/s/turn-001.m4a") == (
        "recordings/s/turn-001",
        "m4a",
    )
    assert split_public_id("charts/task1.svg") == ("charts/task1", "svg")
    # Raw keeps the extension in the id, because nothing is reattached.
    assert split_public_id("charts/task1.txt") == ("charts/task1.txt", "")
    assert split_public_id("a/no-extension") == ("a/no-extension", "")

    storage = _storage()
    # The delivery URL rebuilds exactly the key it was given -- no doubled
    # extension, no lost one.
    assert storage.public_url("charts/task1.svg").endswith("/charts/task1.svg")
    assert storage.public_url("charts/task1.txt").endswith("/charts/task1.txt")


def check_recordings_are_private_and_clips_are_not() -> None:
    """The split the port already draws, mapped onto Cloudinary's own model.

    A voice recording delivered as `upload` is readable by anyone who guesses
    the URL. A seeded listening clip signed per learner buys nothing and costs
    the CDN cache.
    """
    assert is_private("recordings/s/turn-001.m4a") is True
    assert is_private("clips/listening/part1.wav") is False
    # Not fooled by a lookalike prefix.
    assert is_private("recordings-public/x.wav") is False

    storage = _storage()
    assert storage._delivery_type("recordings/s/turn-001.m4a") == "authenticated"
    assert storage._delivery_type("clips/listening/part1.wav") == "upload"

    # A public clip gets the plain CDN URL, with no signature in it at all.
    clip = storage.signed_url("clips/listening/part1.wav")
    assert clip.path.startswith("https://res.cloudinary.com/")
    assert "signature=" not in clip.path

    # A recording gets an expiring download URL instead, because Cloudinary's
    # signed *delivery* URLs authenticate without ever expiring -- a leaked one
    # would work forever.
    recording = storage.signed_url("recordings/s/turn-001.m4a")
    assert "signature=" in recording.path
    assert "expires_at=" in recording.path


def check_folder_scoping() -> None:
    """One account, several environments, no cross-deletion."""
    scoped = _storage(folder="staging")
    assert "/staging/charts/task1.svg" in scoped.public_url("charts/task1.svg")
    # Still private, still expiring — the prefix must not change the split.
    url = scoped.download_url("recordings/s/turn-001.m4a", now=NOW)
    assert parse_qs(urlparse(url.path).query)["public_id"][0] == (
        "staging/recordings/s/turn-001"
    )
    # Trailing and leading slashes are normalised rather than doubling up.
    assert _storage(folder="/staging/").folder == "staging"


def check_traversal_is_refused() -> None:
    storage = _storage()
    for key in ("../etc/passwd", "/absolute", "a/../../b", ""):
        try:
            storage.public_url(key)
        except StorageError:
            pass
        else:  # pragma: no cover
            raise AssertionError(f"accepted unsafe key: {key!r}")
    # `exists` is used as a guard, so it answers rather than raising.
    assert storage.exists("../etc/passwd") is False


def check_construction_is_guarded() -> None:
    for missing in ("cloud_name", "api_key", "api_secret"):
        kwargs = {
            "cloud_name": "c",
            "api_key": "k",
            "api_secret": "s",
            missing: "",
        }
        try:
            CloudinaryStorage(**kwargs)  # type: ignore[arg-type]
        except ValueError:
            pass
        else:  # pragma: no cover
            raise AssertionError(f"constructed without {missing}")


def check_operations_against_a_stub() -> None:
    """The four verbs, against a transport that records what was sent."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        path = request.url.path
        if path.endswith("/upload"):
            return httpx.Response(200, json={"result": "ok"})
        if path.endswith("/destroy"):
            body = request.content.decode("utf-8", "replace")
            found = "turn-001" in body
            return httpx.Response(
                200, json={"result": "ok" if found else "not found"}
            )
        if path.endswith("/download"):
            return httpx.Response(200, content=b"audio-bytes")
        # A plain CDN delivery URL.
        if "missing" in path:
            return httpx.Response(404)
        return httpx.Response(200, content=b"clip-bytes")

    original = httpx.Client.__init__

    def patched(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        original(self, *args, **kwargs)

    httpx.Client.__init__ = patched
    try:
        storage = _storage()

        assert storage.put("recordings/s/turn-001.m4a", b"x", content_type="audio/mp4")
        assert storage.open("recordings/s/turn-001.m4a") == b"audio-bytes"
        assert storage.open("clips/listening/part1.wav") == b"clip-bytes"
        assert storage.exists("clips/listening/part1.wav") is True
        assert storage.exists("clips/listening/missing.wav") is False

        assert storage.delete("recordings/s/turn-001.m4a") is True
        # `{"result": "not found"}` arrives as a 200. Reported as False to
        # match LocalStorage, which the retention job counts on.
        assert storage.delete("recordings/s/turn-999.m4a") is False

        uploads = [r for r in seen if r.url.path.endswith("/upload")]
        assert uploads, "no upload was attempted"
        body = uploads[0].content.decode("utf-8", "replace")
        # Audio must go to the video endpoint, and a re-recorded turn must
        # replace the old one rather than leave the previous attempt playing.
        assert "/video/upload" in str(uploads[0].url)
        assert "overwrite" in body and "invalidate" in body
        assert "signature" in body
        assert API_SECRET not in body

    finally:
        httpx.Client.__init__ = original


def check_errors_name_the_cause() -> None:
    """A bare 401 cannot be told apart from a plan that forbids the type."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401, json={"error": {"message": "Invalid Signature. String to sign - ..."}}
        )

    original = httpx.Client.__init__

    def patched(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        original(self, *args, **kwargs)

    httpx.Client.__init__ = patched
    try:
        try:
            _storage().put("recordings/s/a.m4a", b"x", content_type="audio/mp4")
        except StorageError as error:
            assert "Invalid Signature" in str(error)
            assert "401" in str(error)
        else:  # pragma: no cover
            raise AssertionError("a 401 did not raise")
    finally:
        httpx.Client.__init__ = original


def check_satisfies_the_port() -> None:
    """Interchangeable with LocalStorage, or it is not an adapter."""
    assert isinstance(_storage(), ObjectStorage)


def check_factory_selects_it() -> None:
    import core.config as config_module

    from core.config import Settings
    from core.storage import build_storage

    def with_settings(**kwargs):
        # Blanked by default: Settings reads the real .env, so an unset key
        # would silently pick up the developer's own credentials and the
        # fallback assertions below would test nothing.
        fields = {
            "cloudinary_cloud_name": "",
            "cloudinary_api_key": "",
            "cloudinary_api_secret": "",
            **kwargs,
        }
        # build_storage imports get_settings from core.config at call time, so
        # patching it there is what the factory actually reads.
        saved = config_module.get_settings
        config_module.get_settings = lambda: Settings(**fields)
        try:
            return build_storage(root=Path("."), secret="s")
        finally:
            config_module.get_settings = saved

    assert with_settings(storage_backend="local").name == "local"

    chosen = with_settings(
        storage_backend="cloudinary",
        cloudinary_cloud_name="c",
        cloudinary_api_key="k",
        cloudinary_api_secret="s",
    )
    assert chosen.name == "cloudinary"

    # A half-filled config falls back to local rather than failing to start: a
    # missing cloud name should not take down an app that works perfectly well
    # off local disk.
    assert with_settings(storage_backend="cloudinary").name == "local"
    assert (
        with_settings(storage_backend="cloudinary", cloudinary_cloud_name="c").name
        == "local"
    )


def run() -> None:
    check_signatures_match_the_sdk()
    check_download_urls_match_the_sdk()
    check_audio_is_a_video_resource()
    check_keys_round_trip()
    check_recordings_are_private_and_clips_are_not()
    check_folder_scoping()
    check_traversal_is_refused()
    check_construction_is_guarded()
    check_operations_against_a_stub()
    check_errors_name_the_cause()
    check_satisfies_the_port()
    check_factory_selects_it()

    print("CLOUDINARY STORAGE SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
