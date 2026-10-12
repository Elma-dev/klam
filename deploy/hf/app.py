"""Klam on Hugging Face ZeroGPU — a Gradio Space.

Why Gradio and not the React editor: ZeroGPU is Gradio-SDK-only, and a custom
frontend misses the `postMessage` handshake that sets
`window.supports_zerogpu_headers`, so `@gradio/client` never fetches the identity
token and a logged-in PRO user is billed as anonymous (~2 min/day instead of 40).
See gradio#13209. The React editor therefore stays the local experience; this is
the hosted one.

ZeroGPU rules this file obeys (from HF's own guidance):
  * `import spaces` before torch — it monkey-patches CUDA availability.
  * Models are built at module scope, so the Space's startup pack step captures
    them and the first visitor is not the one who pays to load 15 GB.
  * `@spaces.GPU` wraps the OUTER function that owns the chunk loop, so one call
    covers a whole video rather than one call per chunk.
  * Decorated functions run in a separate process: arguments and returns cross
    by pickle, so this passes paths and returns plain dicts.
  * The declared `duration` is checked against the caller's remaining quota, so
    it is estimated from the media length instead of over-declared.

Deploy with `python deploy/hf/build_space.py` then upload the built directory.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import spaces  # noqa: I001 — must precede torch

HERE = Path(__file__).resolve().parent
os.environ.setdefault("KLAM_FONTS_DIR", str(HERE / "fonts"))
os.environ.setdefault("KLAM_DATA_DIR", tempfile.mkdtemp(prefix="vox-data-"))
sys.path.insert(0, str(HERE))

import gradio as gr  # noqa: E402

from klam.asr.local_gpu import LocalGPUProvider  # noqa: E402
from klam.audio.extract import probe_media  # noqa: E402
from klam.config import Settings  # noqa: E402
from klam.export.video import burn_video, export_subtitles  # noqa: E402
from klam.ffmpeg import require_ffmpeg_libass  # noqa: E402
from klam.pipeline import transcribe_media  # noqa: E402
from klam.schema import CaptionStyle, Project, Segment  # noqa: E402

SETTINGS = Settings()
FONTS = ["Cairo", "Noto Naskh Arabic", "Amiri", "Tajawal", "IBM Plex Sans Arabic", "Inter"]

# ---------------------------------------------------------------- model loading

_PROVIDER: LocalGPUProvider | None = None


def _load() -> None:
    """Build the provider at module scope, as ZeroGPU expects."""
    global _PROVIDER
    try:
        _PROVIDER = LocalGPUProvider()
    except Exception as exc:  # noqa: BLE001 — keep the UI usable without a GPU
        print(f"[vox] model load failed ({type(exc).__name__}: {exc})")
        _PROVIDER = None


_load()


def _provider() -> LocalGPUProvider:
    if _PROVIDER is None:
        raise RuntimeError(
            "Models failed to load at startup — check the Space logs for the "
            "underlying error (torch/transformers pinned, or a CUDA mismatch)."
        )
    return _PROVIDER


# ------------------------------------------------------------------ quota aware


def _seconds(path: str) -> float:
    """Media duration, for sizing the GPU request."""
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", path,
            ],
            capture_output=True, text=True, timeout=30, check=True,
        )
        return float(out.stdout.strip())
    except Exception:  # noqa: BLE001
        return 30.0


def estimate_duration(media_path: str, language: str) -> int:
    """Seconds of GPU to request.

    The platform refuses a call that asks for more than the caller has left, so
    over-declaring costs a user their whole run. Short clips must ask for little.
    """
    return int(max(30, min(300, _seconds(media_path) * 0.9 + 20)))


# ------------------------------------------------------------------- GPU stages


@spaces.GPU(duration=estimate_duration)
def transcribe(media_path: str, language: str) -> dict:
    """The whole transcription: VAD, chunking, ASR, word timings, segmentation."""
    lang = None if language in ("", "auto") else language
    project = transcribe_media(media_path, _provider(), SETTINGS, language=lang)
    return project.model_dump()


# ------------------------------------------------------------------ CPU stages


def _rows(segments: list[dict]) -> list[list]:
    return [
        [round(s["start"], 2), round(s["end"], 2), s["text"].replace("\n", " ")]
        for s in segments
    ]


def _style(**kw) -> CaptionStyle:
    style = CaptionStyle()
    style.font_family = kw["font"]
    style.font_size = float(kw["size"])
    style.color = kw["color"]
    style.active_word.color = kw["active_color"]
    style.active_word.mode = kw["mode"]
    style.position.vertical = kw["position"]
    style.background.opacity = 0.55 if kw["box"] else 0.0
    return style


def _project(media_path: str, rows, kw) -> Project:
    """Rebuild a project from the edited table.

    Media info is probed rather than guessed: a zero width/height would make the
    exporter fall back to a 16:9 canvas and letterbox a vertical clip.
    """
    segments = []
    for row in rows or []:
        start, end, text = float(row[0]), float(row[1]), str(row[2])
        if end <= start or not text.strip():
            continue
        segments.append(
            Segment(id=f"s{len(segments)}", start=start, end=end, text=text.strip())
        )
    return Project(
        media=probe_media(media_path, SETTINGS),
        segments=segments,
        style=_style(**kw),
    )


# ------------------------------------------------------------------- the UI glue


def run_transcribe(media_path: str | None, language: str):
    if not media_path:
        return [], None, "Upload a video first."
    try:
        project = transcribe(media_path, language)
    except Exception as exc:  # noqa: BLE001 — surface it, do not swallow it
        return [], None, f"Failed: {type(exc).__name__}: {exc}"
    segs = project.get("segments", [])
    words = sum(1 for s in segs if s.get("words"))
    return _rows(segs), project, f"{len(segs)} captions, {words} with word timings."


def run_export(media_path: str | None, rows, project, *kw):
    """Burn the edited captions in. CPU work — no GPU request needed."""
    if not media_path or not project:
        return None, "Transcribe something first."
    keys = ("font", "size", "color", "active_color", "mode", "position", "box")
    try:
        built = _project(media_path, rows, dict(zip(keys, kw, strict=True)))
        out = Path(tempfile.mkdtemp(prefix="vox-out-")) / "captioned.mp4"
        burn_video(SETTINGS, media_path, built, str(out), opts=None)
        return str(out), f"Exported {len(built.segments)} captions."
    except Exception as exc:  # noqa: BLE001
        return None, f"Export failed: {type(exc).__name__}: {exc}"


def run_subtitles(media_path: str | None, rows, project, fmt: str, *kw):
    if not project:
        return None
    keys = ("font", "size", "color", "active_color", "mode", "position", "box")
    built = _project(media_path, rows, dict(zip(keys, kw, strict=True)))
    path = Path(tempfile.mkdtemp(prefix="vox-sub-")) / f"captions.{fmt}"
    path.write_text(export_subtitles(built, fmt, SETTINGS), encoding="utf-8")
    return str(path)


def demo() -> gr.Blocks:
    ffmpeg = require_ffmpeg_libass(SETTINGS)

    with gr.Blocks(title="Klam") as ui:
        gr.Markdown(
            "# Klam\n"
            "Arabic and Darija captions, transcribed and burned in on a free "
            "Hugging Face GPU. Upload a clip, edit the captions, export."
        )
        project = gr.State()

        with gr.Row():
            with gr.Column(scale=3):
                media = gr.Video(label="Your video", sources=["upload"])
                status = gr.Markdown()
                with gr.Row():
                    language = gr.Dropdown(
                        ["auto", "ar", "fr", "en"], value="auto", label="Spoken language"
                    )
                    go = gr.Button("Transcribe", variant="primary")

                transcript = gr.Dataframe(
                    headers=["start", "end", "caption"],
                    datatype=["number", "number", "str"],
                    label="Captions — edit the text, times, or delete a row",
                    wrap=True,
                    interactive=True,
                )

            with gr.Column(scale=2):
                gr.Markdown("### Style")
                font = gr.Dropdown(FONTS, value="Cairo", label="Font")
                size = gr.Slider(20, 96, value=48, step=1, label="Size")
                color = gr.ColorPicker(value="#FFFFFF", label="Text colour")
                active_color = gr.ColorPicker(value="#FFE900", label="Highlight colour")
                mode = gr.Dropdown(
                    [("One word at a time", "single"), ("Highlight (karaoke)", "highlight"),
                     ("Word by word", "reveal")],
                    value="single", label="Word effect",
                )
                position = gr.Dropdown(["top", "middle", "bottom"], value="bottom",
                                       label="Position")
                box = gr.Checkbox(value=False, label="Background box")
                export = gr.Button("Export video", variant="primary")
                subtitle_format = gr.Radio(["srt", "vtt", "ass"], value="srt",
                                           label="Subtitle file")
                subtitles = gr.Button("Download subtitles")

                out_video = gr.Video(label="Result", interactive=False)
                out_file = gr.File(label="Subtitle file")
                gr.Markdown(f"`ffmpeg: {ffmpeg}`")
        style_inputs = [font, size, color, active_color, mode, position, box]

        go.click(run_transcribe, [media, language], [transcript, project, status])
        export.click(
            run_export, [media, transcript, project, *style_inputs], [out_video, status]
        )
        subtitles.click(
            run_subtitles,
            [media, transcript, project, subtitle_format, *style_inputs],
            [out_file],
        )

    return ui


if __name__ == "__main__":
    demo().launch()
