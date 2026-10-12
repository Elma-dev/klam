"""Transcription pipeline: media -> audio -> VAD -> chunks -> ASR -> captions.

Owns all timing. Accepts any ``ASRProvider`` and a progress callback.

Timing: a chunk's words come from the first of these that is available —

1. word timings the provider returned with the transcript (a remote endpoint
   serving an aligner alongside the ASR model),
2. the local aligner (MLX Whisper), when this machine has one,
3. otherwise a proportional spread across the chunk.

Sources 1 and 2 both hand us *reference* words from a different model, which
``wordmap.align_transcript`` maps onto the transcript we actually display.
"""

from __future__ import annotations

from collections.abc import Callable

from .aligners import get_aligner
from .asr.base import ASRProvider, ASRResult
from .audio.chunking import make_chunks
from .audio.extract import extract_audio, probe_media
from .config import Settings
from .schema import Language, Project, Word
from .segmentation import SegmentConfig, segment_words
from .wordmap import align_transcript, proportional

Progress = Callable[[str, dict], None]


def _noop(stage: str, info: dict) -> None:  # pragma: no cover
    pass


def _provider_result(provider, chunk, sample_rate: int, language: str) -> ASRResult:
    """Ask the provider for text, and for word timings when it can supply them.

    Providers only have to implement ``transcribe``; ``transcribe_result`` is an
    optional capability (a remote endpoint serving an aligner alongside the ASR
    model), so it is detected rather than required.
    """
    run = getattr(provider, "transcribe_result", None)
    if callable(run):
        return run(chunk, sample_rate, language)
    return ASRResult(text=provider.transcribe(chunk, sample_rate, language))


def transcribe_media(
    media_path: str,
    provider: ASRProvider,
    settings: Settings,
    language: str | None = None,
    progress: Progress | None = None,
) -> Project:
    progress = progress or _noop
    lang = language or settings.language

    progress("extract", {})
    audio = extract_audio(media_path, settings.sample_rate, settings)
    sr = settings.sample_rate

    progress("vad", {})
    chunks = make_chunks(audio, sr, target_duration=settings.chunk_duration)

    seg_cfg = SegmentConfig(
        max_chars_per_line=settings.max_chars_per_line,
        max_lines=settings.max_lines,
        max_duration=settings.max_duration,
    )

    # A provider that returns its own word timings IS the source of truth; do not
    # also construct the local aligner, or a chunk that came back without words
    # would silently pull a multi-gigabyte MLX model onto a machine that never
    # intended to run one.
    provider_has_words = callable(getattr(provider, "transcribe_result", None))
    aligner = None if provider_has_words else get_aligner(settings)
    words_all: list[Word] = []
    aligned = False

    total = len(chunks)
    for i, (start_s, end_s) in enumerate(chunks):
        progress("transcribe", {"index": i, "total": total})
        s, e = int(start_s * sr), int(end_s * sr)
        chunk = audio[s:e]
        result = _provider_result(provider, chunk, sr, lang)
        text = result.text
        if not text.strip():
            continue

        duration = end_s - start_s
        words: list[Word] | None = None

        # A remote endpoint can hand back its own word timings; those win, since
        # they came from the same audio the transcript did.
        if result.ref_words and settings.timed_alignment:
            words = align_transcript(text.split(), result.ref_words, 0.0, duration)
            aligned = True
        elif aligner is not None:
            try:
                words = aligner.align(chunk, sr, text, lang)
                aligned = True
            except Exception:  # noqa: BLE001 — disable alignment, keep the text
                aligner = None

        # Chunk-local, like everything above: the loop below offsets it once.
        if not words:
            words = proportional(text.split(), 0.0, duration)

        for w in words:
            w_start = start_s + max(0.0, w.start)
            w_end = start_s + min(w.end, duration)
            if w_end <= w_start:
                w_end = w_start + 0.001
            words_all.append(
                Word(word=w.word, start=round(w_start, 3), end=round(w_end, 3))
            )

    progress("segment", {"captions": "aligned" if aligned else "proportional"})
    segments = segment_words(words_all, seg_cfg)

    media = probe_media(media_path, settings)
    project = Project(media=media, segments=segments)
    project.language = (
        Language(lang) if lang in Language._value2member_map_ else Language.auto
    )
    progress("done", {"segments": len(segments)})
    return project
