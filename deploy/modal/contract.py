"""The wire format between the Modal service and the app.

Mirrors the OpenAI transcription shape that ``VoxtralProvider`` already posts to
(``backend/src/klam/asr/voxtral.py``), with one addition: ``words``.

``words`` are **not** timings of ``text``. They come from a separate aligner
model, and the app maps them onto ``text`` with ``wordmap.align_transcript``.
``words_source`` says so on the wire, so nobody mistakes our ``words`` for the
OpenAI field of the same name (which *is* timings of ``text``).

Kept free of torch and modal so the routes can be exercised on a CPU machine.
"""

from __future__ import annotations

from pydantic import BaseModel


class WordOut(BaseModel):
    word: str
    start: float
    end: float


class TranscriptionResponse(BaseModel):
    text: str
    language: str | None = None
    duration: float | None = None
    model: str | None = None
    # The aligner's own tokens and timings — a reference track for `text`.
    words: list[WordOut] | None = None
    words_source: str | None = None
