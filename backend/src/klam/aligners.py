"""Word-level alignment via mlx-audio Whisper word timestamps.

Voxtral transcribes the text but returns no timings. Whisper is multilingual
(Arabic included) and decodes the same audio with ``word_timestamps``, giving
per-word boundaries driven by cross-attention. Its transcript can differ from
Voxtral's, so the timings are mapped onto the Voxtral words by sequence
alignment (:mod:`klam.wordmap`) — this is how captions stay in sync.
"""

from __future__ import annotations

import threading

import numpy as np

from .config import Settings
from .model_ref import resolve_mlx_model
from .schema import Word
from .wordmap import align_transcript

_WHISPER_RATE = 16000
_LANG_CODES = {"ar": "ar", "fr": "fr", "en": "en"}


def _resample(audio: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    if src_rate == dst_rate or audio.size == 0:
        return audio
    n = int(round(audio.shape[0] * dst_rate / src_rate))
    src_x = np.linspace(0.0, 1.0, audio.shape[0], endpoint=False)
    dst_x = np.linspace(0.0, 1.0, n, endpoint=False)
    return np.interp(dst_x, src_x, audio).astype(np.float32)


class WhisperAligner:
    name = "whisper"

    def __init__(self, settings: Settings):
        self.settings = settings
        self._model = None
        self._lock = threading.Lock()

    def load(self):
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is not None:
                return self._model
            from mlx_audio.stt import load as load_stt

            self._model = load_stt(
                resolve_mlx_model(self.settings.aligner_model, what="Aligner")
            )
        return self._model

    def align(
        self, audio: np.ndarray, sample_rate: int, text: str, language: str | None = None
    ) -> list[Word]:
        model = self.load()
        waveform = _resample(np.asarray(audio, dtype=np.float32), sample_rate, _WHISPER_RATE)
        out = model.generate(waveform, word_timestamps=True, language=self._language(language))

        ref = [
            Word(word=word["word"].strip(), start=float(word["start"]), end=float(word["end"]))
            for segment in (out.segments or [])
            for word in (segment.get("words") or [])
            if word.get("word", "").strip()
        ]
        duration = waveform.shape[0] / _WHISPER_RATE
        return align_transcript(text.split(), ref, 0.0, duration)

    def _language(self, language: str | None) -> str | None:
        if not language or language == "auto":
            return self.settings.aligner_language or None
        return _LANG_CODES.get(language, language)


def get_aligner(settings: Settings) -> WhisperAligner | None:
    """Return an aligner if timed alignment is enabled and mlx is available."""
    if not settings.timed_alignment:
        return None
    try:
        import mlx_audio  # noqa: F401
    except Exception:  # noqa: BLE001
        return None
    return WhisperAligner(settings)
