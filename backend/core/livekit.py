"""LiveKit access tokens, minted locally.

A LiveKit access token is an HS256 JWT signed with the server's API secret and
carrying a `video` grant that says what the bearer may do. That is the whole
protocol, so it is implemented here with python-jose -- already a dependency for
our own auth -- rather than pulling in an SDK to build a dict and sign it.

Everything is a pure function of its arguments. No network call is involved in
minting a token: the LiveKit server validates the signature itself and never
needs to be asked whether a token is real. That also means this is fully
testable without a running server, which matters because the server is a
container the developer has to start.

The security shape worth stating: the API secret signs tokens that grant room
access, so it is exactly as sensitive as our own JWT secret. It never leaves the
backend, and the client only ever receives a short-lived token scoped to one
room and one identity.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from jose import jwt

#: LiveKit tokens are HS256 by convention and its server expects it.
ALGORITHM = "HS256"

#: Tokens are short-lived. They only need to survive the join handshake, and a
#: leaked one is then worthless within minutes rather than hours.
DEFAULT_TTL_SECONDS = 15 * 60


@dataclass(frozen=True)
class VideoGrant:
    """What the bearer may do, in LiveKit's claim shape.

    Field names are LiveKit's, not ours -- they are serialised verbatim into
    the token and the server matches on them exactly, so renaming any of them
    to something more Pythonic would silently produce a token that grants
    nothing.
    """

    room: str
    room_join: bool = True
    can_publish: bool = True
    can_subscribe: bool = True
    #: Data messages carry the exam's own signalling -- phase changes, the
    #: prep countdown -- alongside the audio.
    can_publish_data: bool = True
    #: Deliberately false for candidates. A participant who can create rooms
    #: can create rooms for anyone, which is not a power a learner needs.
    room_create: bool = False
    room_admin: bool = False

    def to_claim(self) -> dict[str, object]:
        return {
            "room": self.room,
            "roomJoin": self.room_join,
            "canPublish": self.can_publish,
            "canSubscribe": self.can_subscribe,
            "canPublishData": self.can_publish_data,
            "roomCreate": self.room_create,
            "roomAdmin": self.room_admin,
        }


@dataclass(frozen=True)
class AccessToken:
    token: str
    url: str
    room: str
    identity: str
    expires_at: int
    #: Extra fields the client needs but that are not part of the JWT.
    metadata: dict[str, str] = field(default_factory=dict)


def room_name_for(session_id: str) -> str:
    """Deterministic room name for an interview session.

    Derived rather than random so a reconnecting client rejoins the room it
    left instead of creating a second one and talking to nobody.
    """
    return f"interview-{session_id}"


def mint_access_token(
    *,
    api_key: str,
    api_secret: str,
    url: str,
    room: str,
    identity: str,
    name: str = "",
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    grant: VideoGrant | None = None,
    now: int | None = None,
) -> AccessToken:
    """Sign a token admitting `identity` to `room`.

    `now` is injectable so expiry can be tested without waiting.
    """
    if not api_key or not api_secret:
        raise ValueError("LiveKit requires both an API key and an API secret")
    if not identity:
        # LiveKit keys participants by identity, and two participants sharing
        # one identity evict each other. An empty identity would mean every
        # candidate collides.
        raise ValueError("A LiveKit token needs a participant identity")
    if ttl_seconds <= 0:
        raise ValueError("Token TTL must be positive")

    issued = int(time.time()) if now is None else now
    expires = issued + ttl_seconds
    video = (grant or VideoGrant(room=room)).to_claim()

    claims: dict[str, object] = {
        "iss": api_key,
        "sub": identity,
        "jti": f"{identity}-{issued}",
        "nbf": issued,
        "exp": expires,
        "video": video,
    }
    if name:
        claims["name"] = name

    return AccessToken(
        token=jwt.encode(claims, api_secret, algorithm=ALGORITHM),
        url=url,
        room=room,
        identity=identity,
        expires_at=expires,
    )


def decode_for_tests(token: str, api_secret: str) -> dict:
    """Verify and decode a token. Used by tests and by local diagnostics."""
    return jwt.decode(
        token,
        api_secret,
        algorithms=[ALGORITHM],
        # LiveKit tokens carry no audience, and jose insists on one if asked.
        options={"verify_aud": False},
    )
