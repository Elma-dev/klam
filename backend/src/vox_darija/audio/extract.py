"""Audio extraction via FFmpeg/ffprobe."""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

from ..config import Settings
from ..ffmpeg import resolve_ffmpeg, resolve_ffprobe
from ..schema import MediaInfo


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed ({cmd[0]}): {proc.stderr.decode(errors='replace')}"
        )
    return proc


def extract_audio(path: str, sample_rate: int, settings: Settings) -> np.ndarray:
    """Extract mono audio at ``sample_rate`` as float32 in [-1, 1]."""
    ffmpeg = resolve_ffmpeg(settings)
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        path,
        "-f",
        "s16le",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-",
    ]
    proc = _run(cmd)
    return np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0


def probe_media(path: str, settings: Settings) -> MediaInfo:
    """Return duration, width, height via ffprobe (JSON)."""
    import json

    ffprobe = resolve_ffprobe(settings)
    cmd = [
        ffprobe,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        path,
    ]
    proc = _run(cmd)
    info = json.loads(proc.stdout.decode())
    duration = float(info.get("format", {}).get("duration", 0.0) or 0.0)
    width = height = 0
    for stream in info.get("streams", []):
        if stream.get("codec_type") == "video" and width == 0:
            width = int(stream.get("width", 0) or 0)
            height = int(stream.get("height", 0) or 0)
    return MediaInfo(
        filename=Path(path).name, duration=duration, width=width, height=height
    )
