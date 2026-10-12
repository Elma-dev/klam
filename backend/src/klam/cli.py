"""Command-line interface.

Usage:
    klam transcribe video.mp4 --lang ar --output out.srt
    klam transcribe video.mp4 --provider mock --format json
"""

from __future__ import annotations

import argparse
import sys

from .asr.factory import get_provider
from .asr.mock import MockProvider
from .config import Settings, get_settings
from .export import to_srt, to_vtt
from .pipeline import transcribe_media


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="klam", description="Transcribe and caption video."
    )
    sub = p.add_subparsers(dest="command", required=True)

    t = sub.add_parser("transcribe", help="Transcribe a media file")
    t.add_argument("input", help="Path to the media file (mp4/mov/webm/mkv)")
    t.add_argument("--lang", default=None, help="Language: auto/ar/fr/en")
    t.add_argument(
        "--provider", default=None, help="ASR provider: mlx/voxtral/local-gpu/mock"
    )
    t.add_argument("--model", default=None, help="MLX model path")
    t.add_argument("--output", default=None, help="Output file path (default: stdout)")
    t.add_argument(
        "--format", default="srt", choices=["srt", "vtt", "json"], help="Output format"
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    settings: Settings = get_settings()
    if args.lang:
        settings.language = args.lang
    if args.model:
        settings.mlx_model = args.model
    if args.provider:
        settings.asr_provider = args.provider

    provider = (
        MockProvider() if settings.asr_provider == "mock" else get_provider(settings)
    )

    def progress(stage: str, info: dict) -> None:
        print(f"[{stage}] {info}", file=sys.stderr)

    project = transcribe_media(args.input, provider, settings, progress=progress)

    if args.format == "srt":
        text = to_srt(project.segments)
    elif args.format == "vtt":
        text = to_vtt(project.segments)
    else:
        text = project.model_dump_json(indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
