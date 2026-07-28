"""Media routes: serve listening audio.

Audio lives on disk under `backend/media/` in development. In production this
is replaced by object storage with short-lived signed URLs (SRS section 24.2);
`AudioClip.object_key` is already the storage key, so only this resolver
changes.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

router = APIRouter(prefix="/media", tags=["media"])

MEDIA_ROOT = Path(__file__).resolve().parent.parent / "media"

_CONTENT_TYPES = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
}


@router.get("/{object_key:path}")
async def get_media(object_key: str) -> FileResponse:
    """Stream a media file by its storage key."""
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
