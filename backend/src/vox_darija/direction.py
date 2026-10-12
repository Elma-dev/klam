"""Text direction detection (Unicode bidi first-strong heuristic).

Mirrors the HTML ``dir=auto`` algorithm: the direction is decided by the first
strong character (RTL for Arabic/Hebrew, LTR for Latin). Used to set a caption
segment's direction so the preview and the ASS export agree.
"""

from __future__ import annotations

_RTL_BIDI = {"R", "AL"}
_LTR_BIDI = {"L"}


def detect_direction(text: str) -> str:
    """Return ``"rtl"`` or ``"ltr"`` for ``text`` (default ``"ltr"``)."""
    import unicodedata

    for ch in text:
        bidi = unicodedata.bidirectional(ch)
        if bidi in _RTL_BIDI:
            return "rtl"
        if bidi in _LTR_BIDI:
            return "ltr"
    return "ltr"


def has_rtl(text: str) -> bool:
    import unicodedata

    return any(unicodedata.bidirectional(ch) in _RTL_BIDI for ch in text)
