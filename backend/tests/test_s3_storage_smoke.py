"""Smoke test: the S3-compatible storage adapter.

`core/storage.py` argued that an adapter which cannot be run against a real
bucket is a guess. That was right about the risk and wrong about where it sits.
The part that fails silently is the SigV4 signature -- a wrong one is a 403
that reads like bad credentials -- and a signature is exactly the thing that
can be checked without a bucket.

Every expected value below was produced by botocore's independent
implementation (`S3SigV4Auth` / `S3SigV4QueryAuth`) with its clock frozen to
the same instant, then pinned here so CI does not need a 40 MB dependency to
run one assertion. If this adapter's signing drifts, these stop matching.

Regenerate them with botocore installed:

    from botocore.auth import S3SigV4Auth
    import botocore.auth as ba; ba.get_current_datetime = lambda: WHEN

What is still genuinely untested is the network round trip -- real
credentials, bucket policy, CORS, clock skew. No local adapter can cover that,
and the honest gap is now that one rather than the whole file.
"""

from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_s3_storage.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

import httpx  # noqa: E402

from core.s3_storage import (  # noqa: E402
    EMPTY_SHA256,
    S3Storage,
    UNSIGNED_PAYLOAD,
    signing_key,
    uri_encode,
)
from core.storage import ObjectStorage, StorageError  # noqa: E402

#: The credentials from AWS's own signing documentation. Not secret, and using
#: the published pair keeps these comparable to any other implementation.
ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
WHEN = dt.datetime(2013, 5, 24, 0, 0, 0, tzinfo=dt.timezone.utc)
BODY = b"Welcome to Amazon S3."

#: (path_style, key, PUT header signature, presigned GET signature).
#: Cross-checked against botocore; see the module docstring.
VECTORS = [
    (
        False,
        "recordings/sess-1/turn-003.m4a",
        "f5398fb10994d3655ad942d140b9f57638232b66cea8f3f6d88a5312b1cc3dd2",
        "8007d08c324101942ce6afa713963d80c0eb44d6ef721202fac0d18f51fe5b5a",
    ),
    # A dollar sign, which must be percent-encoded in the path but not in a
    # way that also escapes the separators.
    (
        False,
        "test$file.text",
        "e1597ff9ce11084ff783c57808e6d23a187daf25adfeb51196d145185c480704",
        "e6ddc08ed4f8ef4c6c467458995445d6d8e0eb18aa6c54ad9f33bca0fe68981a",
    ),
    # A space and a tilde. `~` is the one character several quote
    # configurations escape and SigV4 requires left alone.
    (
        False,
        "a b/c~d.wav",
        "6660e2b1854b925d7ffcc25b69ca47004436c88cf8584f4bbb4df3b08d6426e6",
        "69a188eae3cfeb2302b1e997c9c0766446e1f1aec94dbdabef3ddab94c857be2",
    ),
    # Path-style addressing, which MinIO and most self-hosted gateways need:
    # the bucket moves from the host into the signed path, so every signature
    # changes.
    (
        True,
        "recordings/sess-1/turn-003.m4a",
        "a7ea9374384f9e17a684b97c6710f2cdcb04ecc7b46f030669472bbd6c721489",
        "7765e3fde7b70517c6c4b0e568ca5748896205bb268306fa895873d472937f62",
    ),
    (
        True,
        "test$file.text",
        "0c7e028a6f5af8fc55720703aa7a85c368866fc4c53fce254b9ce9f1098e41c0",
        "675c89332d4b277576ecb94201d57d26dbd0298f9a6ec861e46ceee90f824cba",
    ),
    (
        True,
        "a b/c~d.wav",
        "2075878786e8123bb876975c451b843d956653cff28ced4d8322f2a918885ecf",
        "386621375efcd6cc2cf66c7b7226d0a202d4923524cc88e34dfd04a6961d7d21",
    ),
]


def _storage(**overrides) -> S3Storage:
    return S3Storage(
        bucket="examplebucket",
        region="us-east-1",
        access_key=ACCESS_KEY,
        secret_key=SECRET_KEY,
        **overrides,
    )


def check_signatures_match_botocore() -> None:
    for path_style, key, put_signature, get_signature in VECTORS:
        storage = _storage(path_style=path_style)

        headers = storage._headers(
            method="PUT",
            key=key,
            payload=BODY,
            extra={"content-type": "text/plain"},
            now=WHEN,
        )
        actual = headers["Authorization"].split("Signature=")[1]
        assert actual == put_signature, (path_style, key, actual)

        presigned = storage.presign(key, ttl_seconds=86400, now=WHEN)
        actual_get = presigned.path.split("X-Amz-Signature=")[1]
        assert actual_get == get_signature, (path_style, key, actual_get)


def check_encoding_rules() -> None:
    """SigV4's unreserved set is narrower than the usual default."""
    # Left alone. `~` escaped is the classic cause of a mismatch that looks
    # like a credentials problem.
    assert uri_encode("aA0-_.~") == "aA0-_.~"
    # Encoded, with uppercase hex.
    assert uri_encode(" ") == "%20"
    assert uri_encode("$") == "%24"
    assert uri_encode("/") == "%2F"
    # Separators survive when the key is a path.
    assert uri_encode("a/b c", encode_slash=False) == "a/b%20c"


def check_signing_key_is_scoped() -> None:
    """A leaked signing key must be good for one day, region and service."""
    base = signing_key(SECRET_KEY, "20130524", "us-east-1", "s3")
    assert base != signing_key(SECRET_KEY, "20130525", "us-east-1", "s3")
    assert base != signing_key(SECRET_KEY, "20130524", "eu-west-1", "s3")
    assert base != signing_key(SECRET_KEY, "20130524", "us-east-1", "s3-outposts")
    assert len(base) == 32


def check_addressing() -> None:
    virtual = _storage()
    assert virtual.host == "examplebucket.s3.amazonaws.com"
    assert virtual.url_for("k/a.m4a") == (
        "https://examplebucket.s3.amazonaws.com/k/a.m4a"
    )

    path = _storage(path_style=True, endpoint="minio.internal:9000", scheme="http")
    assert path.host == "minio.internal:9000"
    assert path.url_for("k/a.m4a") == (
        "http://minio.internal:9000/examplebucket/k/a.m4a"
    )

    # A CDN in front of the bucket changes the URL handed out but not the host
    # the signature was computed against -- getting that backwards produces
    # URLs that 403 only in production.
    cdn = _storage(public_host="media.example.com")
    url = cdn.presign("k/a.m4a", now=WHEN)
    assert url.path.startswith("https://media.example.com/")
    assert (
        url.path.split("X-Amz-Signature=")[1]
        == _storage().presign("k/a.m4a", now=WHEN).path.split("X-Amz-Signature=")[1]
    )


def check_presigned_url_shape() -> None:
    url = _storage().presign("recordings/s/turn-001.m4a", ttl_seconds=900, now=WHEN)
    for required in (
        "X-Amz-Algorithm=AWS4-HMAC-SHA256",
        "X-Amz-Expires=900",
        "X-Amz-SignedHeaders=host",
        "X-Amz-Signature=",
    ):
        assert required in url.path, required
    # The secret must never appear in a URL that gets logged or shared.
    assert SECRET_KEY not in url.path
    assert url.expires_at == int(WHEN.timestamp()) + 900


def check_traversal_is_refused() -> None:
    storage = _storage()
    for key in ("../etc/passwd", "/absolute", "a/../../b", ""):
        try:
            storage.url_for(key)
        except StorageError:
            pass
        else:  # pragma: no cover
            raise AssertionError(f"accepted unsafe key: {key!r}")
    # `exists` is used as a guard, so it answers rather than raising.
    assert storage.exists("../etc/passwd") is False


def check_construction_is_guarded() -> None:
    for missing in ("bucket", "region", "access_key", "secret_key"):
        kwargs = {
            "bucket": "b",
            "region": "r",
            "access_key": "a",
            "secret_key": "s",
            missing: "",
        }
        try:
            S3Storage(**kwargs)  # type: ignore[arg-type]
        except ValueError:
            pass
        else:  # pragma: no cover
            raise AssertionError(f"constructed without {missing}")


def check_payload_hashes() -> None:
    storage = _storage()
    # A body is hashed...
    with_body = storage._headers(method="PUT", key="k", payload=BODY, now=WHEN)
    assert with_body["x-amz-content-sha256"] not in (EMPTY_SHA256, UNSIGNED_PAYLOAD)
    # ...and a request with no body still has to declare the empty hash; S3
    # rejects it otherwise.
    without = storage._headers(method="GET", key="k", payload=None, now=WHEN)
    assert without["x-amz-content-sha256"] == EMPTY_SHA256
    # A presigned URL is signed before the payload exists.
    assert UNSIGNED_PAYLOAD not in storage.presign("k", now=WHEN).path


def check_operations_against_a_stub() -> None:
    """The four verbs, against a transport that records what was sent."""
    seen: list[httpx.Request] = []
    store: dict[str, bytes] = {"recordings/s/turn-001.m4a": BODY}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        key = request.url.path.lstrip("/")
        if request.method == "PUT":
            store[key] = request.content
            return httpx.Response(200)
        if request.method in ("GET", "HEAD"):
            if key not in store:
                return httpx.Response(
                    404, text="<Error><Code>NoSuchKey</Code></Error>"
                )
            return httpx.Response(
                200, content=store[key] if request.method == "GET" else b""
            )
        if request.method == "DELETE":
            if key not in store:
                return httpx.Response(404)
            del store[key]
            return httpx.Response(204)
        return httpx.Response(405)  # pragma: no cover

    original = httpx.Client.__init__

    def patched(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        original(self, *args, **kwargs)

    httpx.Client.__init__ = patched
    try:
        storage = _storage()

        assert storage.open("recordings/s/turn-001.m4a") == BODY
        assert storage.exists("recordings/s/turn-001.m4a") is True
        assert storage.exists("recordings/s/missing.m4a") is False

        assert storage.put("recordings/s/turn-002.m4a", b"new", content_type="audio/mp4")
        assert store["recordings/s/turn-002.m4a"] == b"new"

        assert storage.delete("recordings/s/turn-002.m4a") is True
        # False rather than True for a missing object, matching LocalStorage --
        # the retention job counts what it actually removed.
        assert storage.delete("recordings/s/turn-002.m4a") is False

        try:
            storage.open("recordings/s/missing.m4a")
        except StorageError as error:
            assert "No such object" in str(error)
        else:  # pragma: no cover
            raise AssertionError("missing object did not raise")

        # Every request carried a signature, including the ones with no body.
        assert seen
        for request in seen:
            assert request.headers["Authorization"].startswith("AWS4-HMAC-SHA256 ")
            assert request.headers["x-amz-content-sha256"]
    finally:
        httpx.Client.__init__ = original


def check_errors_name_the_cause() -> None:
    """A bare 403 cannot be told apart from clock skew or a wrong region."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            text=(
                "<Error><Code>SignatureDoesNotMatch</Code>"
                "<Message>...</Message></Error>"
            ),
        )

    original = httpx.Client.__init__

    def patched(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        original(self, *args, **kwargs)

    httpx.Client.__init__ = patched
    try:
        try:
            _storage().put("k/a.m4a", b"x", content_type="audio/mp4")
        except StorageError as error:
            assert "SignatureDoesNotMatch" in str(error)
            assert "403" in str(error)
        else:  # pragma: no cover
            raise AssertionError("a 403 did not raise")
    finally:
        httpx.Client.__init__ = original


def check_satisfies_the_port() -> None:
    """Interchangeable with LocalStorage, or it is not an adapter."""
    assert isinstance(_storage(), ObjectStorage)


def run() -> None:
    check_signatures_match_botocore()
    check_encoding_rules()
    check_signing_key_is_scoped()
    check_addressing()
    check_presigned_url_shape()
    check_traversal_is_refused()
    check_construction_is_guarded()
    check_payload_hashes()
    check_operations_against_a_stub()
    check_errors_name_the_cause()
    check_satisfies_the_port()

    print("S3 STORAGE SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
