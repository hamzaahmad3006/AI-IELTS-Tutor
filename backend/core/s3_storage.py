"""S3-compatible object storage.

An adapter for the `ObjectStorage` port, speaking the S3 REST API over httpx
rather than through boto3 — the same choice the LLM adapters make, and for the
same reason: four verbs and a signature do not justify a 40 MB dependency, and
this way the request shape is visible in the file that sends it.

Works against AWS S3, MinIO, Cloudflare R2, Backblaze B2 and DigitalOcean
Spaces. They differ only in endpoint and whether the bucket goes in the host or
the path, both of which are configuration here.

`core/storage.py` used to say an adapter that cannot be run against a real
bucket is a guess. That was right about the risk and wrong about the remedy:
the part that fails silently is the SigV4 signature, and signatures are exactly
what can be checked without a bucket. The tests verify these against botocore's
independent implementation, so what ships is not a guess about the algorithm.
What is genuinely untested is the network round trip -- credentials, bucket
policy, CORS -- and no local adapter can cover that anyway.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
from dataclasses import dataclass, field
from urllib.parse import quote

import httpx

from core.storage import (
    DEFAULT_TTL_SECONDS,
    SignedUrl,
    StorageError,
    _safe_key,
)

_ALGORITHM = "AWS4-HMAC-SHA256"
#: SHA-256 of the empty string. Required as the payload hash on requests with
#: no body; S3 rejects them without it.
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
#: Sent instead of a body hash on presigned URLs, which are signed before the
#: payload exists.
UNSIGNED_PAYLOAD = "UNSIGNED-PAYLOAD"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hmac(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


def uri_encode(value: str, *, encode_slash: bool = True) -> str:
    """Percent-encode per the SigV4 rules.

    Not `urllib.quote`'s defaults: SigV4 requires the unreserved set to be
    exactly A-Z a-z 0-9 - _ . ~, and everything else encoded with uppercase
    hex. `~` in particular is left alone here and escaped by some quote
    configurations, which produces a signature mismatch that reads as a
    credentials problem.
    """
    safe = "-_.~" + ("" if encode_slash else "/")
    return quote(value, safe=safe)


def signing_key(secret: str, date_stamp: str, region: str, service: str) -> bytes:
    """Derive the date/region/service-scoped signing key.

    Scoped rather than using the secret directly, so a leaked signing key is
    good for one day, one region and one service instead of the account.
    """
    key = _hmac(f"AWS4{secret}".encode("utf-8"), date_stamp)
    key = _hmac(key, region)
    key = _hmac(key, service)
    return _hmac(key, "aws4_request")


def canonical_request(
    *,
    method: str,
    path: str,
    query: str,
    headers: dict[str, str],
    signed_headers: str,
    payload_hash: str,
) -> str:
    """Build the canonical request string that gets hashed into the signature.

    Header values are stripped and their names lowercased, and the list has to
    be sorted the same way the `SignedHeaders` list is. A mismatch between the
    two is the single most common cause of a SigV4 403.
    """
    canonical_headers = "".join(
        f"{name.lower()}:{str(value).strip()}\n"
        for name, value in sorted(headers.items(), key=lambda kv: kv[0].lower())
    )
    return "\n".join(
        [
            method.upper(),
            path,
            query,
            canonical_headers,
            signed_headers,
            payload_hash,
        ]
    )


def string_to_sign(*, amz_date: str, scope: str, request: str) -> str:
    return "\n".join([_ALGORITHM, amz_date, scope, _sha256(request.encode("utf-8"))])


@dataclass
class S3Storage:
    """Objects in an S3-compatible bucket."""

    bucket: str
    region: str
    access_key: str
    secret_key: str
    #: Host only, no scheme — "s3.amazonaws.com", "minio.internal:9000".
    endpoint: str = "s3.amazonaws.com"
    scheme: str = "https"
    #: MinIO and most self-hosted gateways need the bucket in the path.
    #: AWS and R2 put it in the host.
    path_style: bool = False
    #: Overrides the derived host in the public URL, for a CDN in front of the
    #: bucket. The signature is still computed against the real host.
    public_host: str = ""
    timeout_s: float = 30.0
    service: str = "s3"

    name: str = field(default="s3", init=False)

    def __post_init__(self) -> None:
        for label, value in (
            ("bucket", self.bucket),
            ("region", self.region),
            ("access key", self.access_key),
            ("secret key", self.secret_key),
        ):
            if not value:
                raise ValueError(f"S3 storage requires a {label}")

    # -- addressing ---------------------------------------------------------

    @property
    def host(self) -> str:
        if self.path_style:
            return self.endpoint
        return f"{self.bucket}.{self.endpoint}"

    def _path(self, key: str) -> str:
        safe = _safe_key(key)
        # The slash between segments must survive encoding; everything inside
        # a segment must not.
        encoded = uri_encode(safe, encode_slash=False)
        if self.path_style:
            return f"/{uri_encode(self.bucket)}/{encoded}"
        return f"/{encoded}"

    def url_for(self, key: str) -> str:
        return f"{self.scheme}://{self.host}{self._path(key)}"

    # -- signing ------------------------------------------------------------

    def _headers(
        self,
        *,
        method: str,
        key: str,
        payload: bytes | None,
        extra: dict[str, str] | None = None,
        now: dt.datetime | None = None,
    ) -> dict[str, str]:
        """Sign a request with SigV4 in the Authorization header."""
        moment = now or dt.datetime.now(dt.timezone.utc)
        amz_date = moment.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = moment.strftime("%Y%m%d")
        payload_hash = _sha256(payload) if payload is not None else EMPTY_SHA256

        headers = {
            "host": self.host,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
            **{k.lower(): v for k, v in (extra or {}).items()},
        }
        signed_headers = ";".join(sorted(headers))

        request = canonical_request(
            method=method,
            path=self._path(key),
            query="",
            headers=headers,
            signed_headers=signed_headers,
            payload_hash=payload_hash,
        )
        scope = f"{date_stamp}/{self.region}/{self.service}/aws4_request"
        signature = hmac.new(
            signing_key(self.secret_key, date_stamp, self.region, self.service),
            string_to_sign(amz_date=amz_date, scope=scope, request=request).encode(
                "utf-8"
            ),
            hashlib.sha256,
        ).hexdigest()

        return {
            **headers,
            "Authorization": (
                f"{_ALGORITHM} Credential={self.access_key}/{scope}, "
                f"SignedHeaders={signed_headers}, Signature={signature}"
            ),
        }

    def presign(
        self,
        key: str,
        *,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        method: str = "GET",
        now: dt.datetime | None = None,
    ) -> SignedUrl:
        """A URL that grants one object for a limited time, with no server in
        the path.

        This is the reason to bother with S3 at all: audio is served straight
        from the bucket instead of streaming through the API process, so a
        recording playing does not occupy a worker.
        """
        moment = now or dt.datetime.now(dt.timezone.utc)
        amz_date = moment.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = moment.strftime("%Y%m%d")
        scope = f"{date_stamp}/{self.region}/{self.service}/aws4_request"

        headers = {"host": self.host}
        signed_headers = ";".join(sorted(headers))

        # Sorted by key, and encoded before sorting — SigV4 orders by the
        # encoded form, which differs for anything containing a slash.
        params = {
            "X-Amz-Algorithm": _ALGORITHM,
            "X-Amz-Credential": f"{self.access_key}/{scope}",
            "X-Amz-Date": amz_date,
            "X-Amz-Expires": str(ttl_seconds),
            "X-Amz-SignedHeaders": signed_headers,
        }
        query = "&".join(
            f"{uri_encode(name)}={uri_encode(value)}"
            for name, value in sorted(params.items())
        )

        request = canonical_request(
            method=method,
            path=self._path(key),
            query=query,
            headers=headers,
            signed_headers=signed_headers,
            # The body does not exist yet, so it cannot be hashed.
            payload_hash=UNSIGNED_PAYLOAD,
        )
        signature = hmac.new(
            signing_key(self.secret_key, date_stamp, self.region, self.service),
            string_to_sign(amz_date=amz_date, scope=scope, request=request).encode(
                "utf-8"
            ),
            hashlib.sha256,
        ).hexdigest()

        host = self.public_host or self.host
        return SignedUrl(
            path=(
                f"{self.scheme}://{host}{self._path(key)}"
                f"?{query}&X-Amz-Signature={signature}"
            ),
            expires_at=int(moment.timestamp()) + ttl_seconds,
        )

    # -- ObjectStorage ------------------------------------------------------

    def put(self, key: str, data: bytes, *, content_type: str) -> str:
        headers = self._headers(
            method="PUT",
            key=key,
            payload=data,
            extra={"content-type": content_type or "application/octet-stream"},
        )
        with httpx.Client(timeout=self.timeout_s) as client:
            response = client.put(self.url_for(key), content=data, headers=headers)
        if response.status_code >= 300:
            raise StorageError(_describe(response, key))
        return key

    def open(self, key: str) -> bytes:
        headers = self._headers(method="GET", key=key, payload=None)
        with httpx.Client(timeout=self.timeout_s) as client:
            response = client.get(self.url_for(key), headers=headers)
        if response.status_code == 404:
            raise StorageError(f"No such object: {key}")
        if response.status_code >= 300:
            raise StorageError(_describe(response, key))
        return response.content

    def exists(self, key: str) -> bool:
        try:
            headers = self._headers(method="HEAD", key=key, payload=None)
        except StorageError:
            # An unsafe key cannot exist; callers use this as a guard and
            # should not have to catch for that.
            return False
        with httpx.Client(timeout=self.timeout_s) as client:
            response = client.head(self.url_for(key), headers=headers)
        return response.status_code == 200

    def delete(self, key: str) -> bool:
        headers = self._headers(method="DELETE", key=key, payload=None)
        with httpx.Client(timeout=self.timeout_s) as client:
            response = client.delete(self.url_for(key), headers=headers)
        # S3 returns 204 whether or not the object was there. Reported as
        # False for a missing object to match LocalStorage, which callers
        # already rely on for the retention job's counts.
        if response.status_code == 404:
            return False
        if response.status_code >= 300:
            raise StorageError(_describe(response, key))
        return True

    def signed_url(
        self, key: str, *, ttl_seconds: int = DEFAULT_TTL_SECONDS
    ) -> SignedUrl:
        return self.presign(key, ttl_seconds=ttl_seconds)


def _describe(response: httpx.Response, key: str) -> str:
    """A message that says what went wrong, not just that it did.

    S3 errors arrive as an XML body with a machine code in it; without pulling
    that out, an operator sees "403" and cannot tell a clock skew from a bucket
    policy from a wrong region.
    """
    body = response.text or ""
    code = ""
    if "<Code>" in body:
        code = body.split("<Code>", 1)[1].split("</Code>", 1)[0]
    return f"S3 {response.status_code} {code or 'error'} for {key}".strip()
