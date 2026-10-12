"""Burned-in export integration test (requires FFmpeg with libass).

Verifies that a caption actually changes pixels: a black video exported with a
caption has a brighter subtitle region than one exported without.
"""

from __future__ import annotations

import re
import subprocess

import pytest

from klam.config import Settings
from klam.export import ExportOptions, build_ass, burn_video
from klam.ffmpeg import has_libass, resolve_ffmpeg
from klam.schema import Direction, MediaInfo, Project, Segment

settings = Settings()
FFMPEG = resolve_ffmpeg(settings)

pytestmark = pytest.mark.skipif(
    not has_libass(FFMPEG), reason="ffmpeg with libass not available"
)


def _blank_video(path: str, seconds: float = 2.0) -> None:
    cmd = [
        FFMPEG,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        f"color=c=black:s=320x240:d={seconds}",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=16000:cl=mono",
        "-shortest",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def _stat(path: str, at: float, crop: str, key: str = "YMAX") -> float:
    cmd = [
        FFMPEG,
        "-hide_banner",
        "-loglevel",
        "info",
        "-ss",
        str(at),
        "-i",
        path,
        "-vf",
        f"crop={crop},signalstats,metadata=print:key=lavfi.signalstats.{key}",
        "-frames:v",
        "1",
        "-f",
        "null",
        "-",
    ]
    out = subprocess.run(cmd, capture_output=True).stderr.decode(errors="replace")
    match = re.search(rf"{key}=([0-9.]+)", out)
    assert match, out[-500:]
    return float(match.group(1))


def _project(with_caption: bool) -> Project:
    segments = (
        [Segment(id="1", start=0.0, end=2.0, text="مرحبا", dir=Direction.rtl)]
        if with_caption
        else []
    )
    return Project(
        media=MediaInfo(filename="blank.mp4", duration=2.0, width=320, height=240),
        language="ar",
        segments=segments,
    )


def test_ass_generation_for_export() -> None:
    ass = build_ass(_project(True), 320, 240, 1080)
    assert "PlayResX: 320" in ass
    assert "Dialogue:" in ass


def test_burn_in_changes_pixels(tmp_path) -> None:
    blank = tmp_path / "blank.mp4"
    _blank_video(str(blank))

    none = tmp_path / "none.mp4"
    yes = tmp_path / "yes.mp4"
    burn_video(settings, str(blank), _project(False), str(none), ExportOptions())
    burn_video(settings, str(blank), _project(True), str(yes), ExportOptions())

    assert none.exists() and yes.exists()

    region = "320:120:0:120"  # band where the caption sits
    ymax_none = _stat(str(none), 1.0, region)
    ymax_yes = _stat(str(yes), 1.0, region)
    assert ymax_yes > ymax_none + 50.0, (ymax_none, ymax_yes)
