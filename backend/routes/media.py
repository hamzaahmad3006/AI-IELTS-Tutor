"""Media routes: serve stored audio.

Audio lives on disk under `backend/media/`, keyed rather than pathed, so a
hosted backend is an adapter change rather than a rewrite. These routes serve
the local backend; with STORAGE_BACKEND=cloudinary the same public/private
split is enforced by Cloudinary's own delivery types and this route is bypassed
for media that has been uploaded there.

Two classes of object are served here and they need different rules. Seeded
listening clips are identical for every learner and public by nature. A
recording of someone answering a speaking question is not, and without a
signature `/media/<key>` is readable by anyone who can guess a key.

So anything under the recordings prefix requires a valid signature, and
everything else does not. Requiring one for seeded clips would mean minting a
URL per clip per learner for content that is the same for all of them.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse

from core.config import get_settings
from core.storage import RECORDINGS_PREFIX, verify

router = APIRouter(prefix="/media", tags=["media"])

MEDIA_ROOT = Path(__file__).resolve().parent.parent / "media"

_CONTENT_TYPES = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    # Task 1 charts. Served as image/svg+xml rather than the octet-stream
    # fallback, which a client downloads instead of rendering.
    ".svg": "image/svg+xml",
    # The screen-reader alternative that ships beside each chart.
    ".txt": "text/plain; charset=utf-8",
}


@router.get("/{object_key:path}")
async def get_media(
    object_key: str,
    expires: int | None = Query(default=None),
    sig: str | None = Query(default=None),
) -> FileResponse:
    """Stream a media file by its storage key.

    Recordings require a signature; public clips do not. The check happens
    before the file is touched, so an unsigned request for a recording cannot
    even confirm whether the key exists.
    """
    if object_key.startswith(f"{RECORDINGS_PREFIX}/"):
        if expires is None or not sig:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This recording requires a signed link",
            )
        if not verify(object_key, expires, sig, get_settings().jwt_secret):
            # One message for a bad signature and an expired one: telling them
            # apart tells an attacker whether they got the signature right.
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This link is invalid or has expired",
            )

    candidate = (MEDIA_ROOT / object_key).resolve()

    # Path traversal guard: the resolved path must stay inside MEDIA_ROOT.
    if not candidate.is_relative_to(MEDIA_ROOT.resolve()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid media path"
        )
    if not candidate.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Media not found"
        )

    media_type = _CONTENT_TYPES.get(candidate.suffix.lower(), "application/octet-stream")
    return FileResponse(candidate, media_type=media_type)
