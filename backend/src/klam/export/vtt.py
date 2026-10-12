"""VTT export."""

from __future__ import annotations

from ..schema import Segment
from .srt import _ts


def to_vtt(segments: list[Segment]) -> str:
    blocks = ["WEBVTT"]
    for i, seg in enumerate(segments, 1):
        blocks.append(
            f"\n{i}\n{_ts(seg.start).replace(',', '.')} --> {_ts(seg.end).replace(',', '.')}\n{seg.text}"
        )
    return "\n".join(blocks) + "\n"
