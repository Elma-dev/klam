"""ASR provider interface.

Transcription is text plus optional timing, because the models split that way:
Voxtral returns plain text with no timestamps, while a separate aligner can
supply word boundaries.

* ``ASRProvider.transcribe(audio, sample_rate, language) -> str`` — the required
  surface. A provider turns a chunk of raw 16 kHz mono audio into text.
* ``WordTimedProvider.transcribe_result(...) -> ASRResult`` — optional. A
  provider that can also supply word timings returns them as ``ref_words``.
* ``Pipeline`` (see ``pipeline.py``) owns timing: it runs VAD + chunking, asks
  the provider for text (and timings if it has them), then produces timed
  ``Segment`` objects.

``ref_words`` are **not** timings of ``text``: they come from a different model
and are mapped onto ``text`` by ``wordmap.align_transcript``. A remote endpoint
can therefore return one model's transcript next to another's word boundaries.

Providers stay small and swappable (MLX, Voxtral, Whisper, mock).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ..schema import Word


@dataclass(slots=True)
class ASRResult:
    """A transcript, plus optional word timings from a secondary aligner."""

    text: str
    ref_words: list[Word] | None = field(default=None)


@runtime_checkable
class ASRProvider(Protocol):
    name: str

    def transcribe(self, audio, sample_rate: int, language: str) -> str:
        """Transcribe a chunk of mono float32 audio (16 kHz) to text."""
        ...


@runtime_checkable
class WordTimedProvider(Protocol):
    """Optional capability: a provider that can also report word timings."""

    def transcribe_result(
        self, audio, sample_rate: int, language: str
    ) -> ASRResult:
        """Transcribe, and return reference word timings when available."""
        ...
