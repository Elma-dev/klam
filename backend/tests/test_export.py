from __future__ import annotations

from vox_darija.export import to_srt, to_vtt
from vox_darija.schema import Segment


def test_srt_format() -> None:
    segs = [Segment(id="a", start=0.0, end=2.5, text="مرحبا")]
    out = to_srt(segs)
    assert out == "1\n00:00:00,000 --> 00:00:02,500\nمرحبا\n"


def test_srt_multi_segment() -> None:
    segs = [
        Segment(id="a", start=0.0, end=1.0, text="one"),
        Segment(id="b", start=1.0, end=2.0, text="two"),
    ]
    out = to_srt(segs)
    assert (
        "1\n00:00:00,000 --> 00:00:01,000\none\n\n2\n00:00:01,000 --> 00:00:02,000\ntwo"
        in out
    )


def test_vtt_header() -> None:
    segs = [Segment(id="a", start=0.0, end=2.5, text="مرحبا")]
    out = to_vtt(segs)
    assert out.startswith("WEBVTT\n")
    assert "00:00:00.000 --> 00:00:02.500" in out
