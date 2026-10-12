"""Burned-in video export (libass) and subtitle/project file exports."""

from __future__ import annotations

import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..config import Settings
from ..ffmpeg import require_ffmpeg_libass
from ..paths import resolve_fonts_dir
from ..schema import Project
from .ass import build_ass
from .srt import to_srt
from .vtt import to_vtt

_ASPECTS = {"16:9": (1920, 1080), "1:1": (1080, 1080), "9:16": (1080, 1920)}


@dataclass
class ExportOptions:
    aspect: str = "source"  # source | 16:9 | 1:1 | 9:16
    mode: str = "fit"  # fit (letterbox) | fill (crop)
    crf: int = 20
    preset: str = "medium"


def _even(n: int) -> int:
    return n - (n % 2)


def target_size(project: Project, opts: ExportOptions) -> tuple[int, int]:
    if opts.aspect == "source":
        w = project.media.width or 1920
        h = project.media.height or 1080
    else:
        w, h = _ASPECTS[opts.aspect]
    return _even(w), _even(h)


def _quote(path: str) -> str:
    return "'" + path.replace("\\", "\\\\").replace("'", "\\'") + "'"


def build_vf(
    width: int, height: int, opts: ExportOptions, ass_path: str, fonts_dir: str | None
) -> str:
    ass = f"ass=filename={_quote(ass_path)}"
    if fonts_dir:
        ass += f":fontsdir={_quote(fonts_dir)}"
    if opts.aspect == "source":
        return ass
    if opts.mode == "fill":
        return (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},{ass}"
        )
    return (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,{ass}"
    )


def burn_video(
    settings: Settings,
    input_path: str,
    project: Project,
    out_path: str,
    opts: ExportOptions | None = None,
    progress: Callable[[float], None] | None = None,
) -> str:
    opts = opts or ExportOptions()
    ffmpeg = require_ffmpeg_libass(settings)
    width, height = target_size(project, opts)
    fonts_dir = resolve_fonts_dir(settings)

    with tempfile.TemporaryDirectory() as td:
        ass_path = Path(td) / "captions.ass"
        ass_path.write_text(
            build_ass(project, width, height, settings.reference_height),
            encoding="utf-8",
        )
        vf = build_vf(
            width, height, opts, str(ass_path), str(fonts_dir) if fonts_dir else None
        )
        cmd = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-progress",
            "pipe:1",
            "-nostats",
            "-i",
            input_path,
            "-vf",
            vf,
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-preset",
            opts.preset,
            "-crf",
            str(opts.crf),
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            out_path,
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        duration = project.media.duration or 0.0
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.decode(errors="replace").strip()
            if line.startswith("out_time_ms=") and duration and progress:
                value = line.split("=", 1)[1]
                if value.isdigit():
                    progress(min(1.0, (int(value) / 1_000_000) / duration))
        proc.wait()
        if proc.returncode != 0:
            err = proc.stderr.read().decode(errors="replace") if proc.stderr else ""
            raise RuntimeError(f"ffmpeg export failed: {err[-2000:]}")
    if progress:
        progress(1.0)
    return out_path


def export_subtitles(project: Project, fmt: str, settings: Settings) -> str:
    """Return a subtitle/project file as text for the given format."""
    if fmt == "srt":
        return to_srt(project.segments)
    if fmt == "vtt":
        return to_vtt(project.segments)
    if fmt == "ass":
        width = project.media.width or 1920
        height = project.media.height or 1080
        return build_ass(project, width, height, settings.reference_height)
    if fmt == "json":
        return project.model_dump_json(indent=2)
    raise ValueError(f"unknown format: {fmt}")
