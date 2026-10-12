"""SRT export."""

from __future__ import annotations

from ..schema import Segment


def _ts(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    millis = int(round((secs - int(secs)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{int(secs):02d},{millis:03d}"


def to_srt(segments: list[Segment]) -> str:
    blocks = []
    for i, seg in enumerate(segments, 1):
        blocks.append(f"{i}\n{_ts(seg.start)} --> {_ts(seg.end)}\n{seg.text}")
    return "\n\n".join(blocks) + ("\n" if blocks else "")
