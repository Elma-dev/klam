"""Resolution of the ffmpeg/ffprobe binaries and libass availability.

Homebrew's ``ffmpeg`` formula no longer ships libass; ``ffmpeg-full`` does. We
auto-detect a libass-capable build and fail with a clear message otherwise.
"""

from __future__ import annotations

import functools
import os
import shutil
import subprocess

from .config import Settings

# Prefer a libass-capable build; fall back to whatever is on PATH.
_FFMPEG_CANDIDATES = [
    "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg",
    "/usr/local/opt/ffmpeg-full/bin/ffmpeg",
    "/opt/homebrew/bin/ffmpeg",
    "ffmpeg",
]


@functools.lru_cache(maxsize=16)
def has_libass(binary: str) -> bool:
    try:
        out = subprocess.run(
            [binary, "-hide_banner", "-filters"],
            capture_output=True,
            timeout=20,
        ).stdout
    except Exception:  # noqa: BLE001
        return False
    return b" subtitles " in out and b" ass " in out


def _which(candidate: str) -> str | None:
    if os.path.isabs(candidate):
        return candidate if os.path.exists(candidate) else None
    return shutil.which(candidate)


def resolve_ffmpeg(settings: Settings) -> str:
    if settings.ffmpeg_bin:
        return settings.ffmpeg_bin
    for candidate in _FFMPEG_CANDIDATES:
        path = _which(candidate)
        if path and has_libass(path):
            return path
    return "ffmpeg"


def resolve_ffprobe(settings: Settings, ffmpeg: str | None = None) -> str:
    if settings.ffprobe_bin:
        return settings.ffprobe_bin
    ff = ffmpeg or resolve_ffmpeg(settings)
    sibling = os.path.join(os.path.dirname(ff), "ffprobe")
    if os.path.exists(sibling):
        return sibling
    found = shutil.which("ffprobe")
    return found or "ffprobe"


def require_ffmpeg_libass(settings: Settings) -> str:
    """Return a libass-capable ffmpeg path or raise a clear error."""
    ff = resolve_ffmpeg(settings)
    if not has_libass(ff):
        raise RuntimeError(
            "Burn-in export needs an FFmpeg built with libass. Install it with:\n"
            "  brew install ffmpeg-full\n"
            "then set VOX_FFMPEG_BIN=/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg\n"
            "(see docs/PLAN.md)."
        )
    return ff
