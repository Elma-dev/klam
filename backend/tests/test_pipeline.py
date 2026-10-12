from __future__ import annotations

import shutil
import wave

import numpy as np
import pytest

from vox_darija.asr.base import ASRResult
from vox_darija.asr.mock import MockProvider
from vox_darija.config import Settings
from vox_darija.export import to_srt
from vox_darija.pipeline import transcribe_media
from vox_darija.schema import Word

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe not available",
)


def _tone(freq: float, dur: float, sr: int = 16000, amp: float = 0.3) -> np.ndarray:
    t = np.arange(int(dur * sr)) / sr
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _write_wav(path: str, audio: np.ndarray, sr: int = 16000) -> None:
    pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def test_upload_transcribe_export_pipeline(tmp_path) -> None:
    sr = 16000
    audio = np.concatenate(
        [
            np.zeros(int(0.3 * sr), dtype=np.float32),
            _tone(440, 2.0),
            np.zeros(int(0.5 * sr), dtype=np.float32),
            _tone(880, 2.0),
            np.zeros(int(0.3 * sr), dtype=np.float32),
        ]
    )
    media = tmp_path / "sample.wav"
    _write_wav(str(media), audio)

    settings = Settings(
        data_dir=tmp_path / "data", asr_provider="mock", timed_alignment=False
    )
    provider = MockProvider(transcript="مرحبا بكم في الدارجة. اليوم غادي نتعلمو.")

    stages: list[str] = []
    project = transcribe_media(
        str(media),
        provider,
        settings,
        language="ar",
        progress=lambda s, i: stages.append(s),
    )

    assert project.segments, "expected non-empty segments"
    assert "extract" in stages and "done" in stages

    prev = -1.0
    for seg in project.segments:
        assert seg.start >= prev - 1e-6
        assert seg.end >= seg.start
        prev = seg.end

    srt = to_srt(project.segments)
    assert "مرحبا" in srt
    assert " --> " in srt


class _RefProvider:
    """Stands in for a remote endpoint that returns its own word timings."""

    name = "ref"

    def __init__(self) -> None:
        self.calls = 0

    def transcribe(self, audio, sample_rate: int, language: str) -> str:
        return self.transcribe_result(audio, sample_rate, language).text

    def transcribe_result(self, audio, sample_rate: int, language: str) -> ASRResult:
        self.calls += 1
        # Chunk-local, exactly like the local aligner's output.
        return ASRResult(
            text="واحد اثنان",
            ref_words=[
                Word(word="واحد", start=0.0, end=0.2),
                Word(word="اثنان", start=0.2, end=0.4),
            ],
        )


def test_provider_timings_are_used_and_offset_exactly_once(tmp_path) -> None:
    """Regression: the fallback used to be spread in absolute time and then
    offset again, collapsing every word of a later chunk into its last second."""
    sr = 16000
    audio = np.concatenate(
        [
            np.zeros(int(0.3 * sr), dtype=np.float32),
            _tone(440, 2.0),
            np.zeros(int(0.5 * sr), dtype=np.float32),
            _tone(880, 2.0),
            np.zeros(int(0.3 * sr), dtype=np.float32),
        ]
    )
    media = tmp_path / "sample.wav"
    _write_wav(str(media), audio)

    settings = Settings(
        data_dir=tmp_path / "data", asr_provider="voxtral", timed_alignment=True
    )
    provider = _RefProvider()
    project = transcribe_media(str(media), provider, settings, language="ar")

    words = [w for seg in project.segments for w in (seg.words or [])]
    assert provider.calls >= 2, "expected more than one VAD chunk"
    assert len(words) >= 4, "expected the provider's words on every chunk"

    # The references sit in the first 0.4s of each chunk. Spread proportionally
    # they would run to each chunk's end instead, and with the old double offset
    # a second chunk landed past the end of the clip.
    total = len(audio) / sr
    assert max(w.end for w in words) < total * 0.9

    for earlier, later in zip(words, words[1:], strict=False):
        assert later.start >= earlier.start - 1e-9
        assert later.end >= later.start


def test_proportional_fallback_stays_inside_its_chunk(tmp_path) -> None:
    """No aligner and no provider timings: the words are spread across the chunk
    they came from. They used to be spread in absolute time and then offset a
    second time, which pushed later chunks past the end of the clip."""
    sr = 16000
    audio = np.concatenate(
        [
            np.zeros(int(0.3 * sr), dtype=np.float32),
            _tone(440, 2.0),
            np.zeros(int(0.5 * sr), dtype=np.float32),
            _tone(880, 2.0),
            np.zeros(int(0.3 * sr), dtype=np.float32),
        ]
    )
    media = tmp_path / "sample.wav"
    _write_wav(str(media), audio)

    settings = Settings(
        data_dir=tmp_path / "data", asr_provider="mock", timed_alignment=False
    )
    project = transcribe_media(
        str(media), MockProvider(transcript="واحد اثنان ثلاثة"), settings, language="ar"
    )

    words = [w for seg in project.segments for w in (seg.words or [])]
    assert words
    total = len(audio) / sr
    assert min(w.start for w in words) >= 0.0
    assert max(w.end for w in words) <= total + 1e-6
