"""MLXAudioProvider — Voxtral via mlx-audio on Apple Silicon.

Two modes, selected by ``Settings.mlx_mode``:

* ``inprocess`` — call ``mlx_audio.stt`` directly (loads the model into memory).
* ``http`` — POST to the mlx-audio server's OpenAI-compatible
  ``/v1/audio/transcriptions`` endpoint.

The model returns text only (no timestamps, no language), so this provider is a
pure text source; timing is handled upstream by the pipeline.
"""

from __future__ import annotations

import os
import tempfile
import threading

import numpy as np

from ..audio.wav import write_wav
from ..config import Settings
from ..model_ref import resolve_mlx_model


class MLXAudioProvider:
    name = "mlx"

    def __init__(self, settings: Settings):
        self.settings = settings
        self._model = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # Model loading (in-process mode)
    # ------------------------------------------------------------------ #
    def load(self):
        """Load the model (cached). Raises if the path is missing."""
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is not None:
                return self._model
            from mlx_audio.stt import load as load_stt

            self._model = load_stt(
                resolve_mlx_model(self.settings.mlx_model, what="ASR")
            )
        return self._model

    # ------------------------------------------------------------------ #
    # ASRProvider interface
    # ------------------------------------------------------------------ #
    def transcribe(self, audio, sample_rate: int, language: str) -> str:
        if self.settings.mlx_mode == "http":
            return self._transcribe_http(audio, sample_rate, language)
        return self._transcribe_inprocess(audio, sample_rate)

    # ------------------------------------------------------------------ #
    # In-process
    # ------------------------------------------------------------------ #
    def _transcribe_inprocess(self, audio: np.ndarray, sample_rate: int) -> str:
        model = self.load()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            path = tmp.name
        try:
            self._write_wav(path, audio, sample_rate)
            out = model.generate(path)
            return getattr(out, "text", "").strip()
        finally:
            with self._suppress():
                os.remove(path)

    # ------------------------------------------------------------------ #
    # HTTP
    # ------------------------------------------------------------------ #
    def _transcribe_http(
        self, audio: np.ndarray, sample_rate: int, language: str
    ) -> str:
        import httpx

        url = f"{self.settings.mlx_base_url.rstrip('/')}/v1/audio/transcriptions"
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            path = tmp.name
        try:
            self._write_wav(path, audio, sample_rate)
            with open(path, "rb") as fh:
                files = {"file": ("audio.wav", fh, "audio/wav")}
                data = {
                    "model": self.settings.mlx_model,
                    "response_format": "json",
                }
                if language and language != "auto":
                    data["language"] = language
                resp = httpx.post(
                    url, files=files, data=data, timeout=self.settings.mlx_timeout
                )
                resp.raise_for_status()
                return (resp.json().get("text") or "").strip()
        finally:
            with self._suppress():
                os.remove(path)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _write_wav(path: str, audio: np.ndarray, sample_rate: int) -> None:
        write_wav(path, audio, sample_rate)

    @staticmethod
    def _suppress():
        import contextlib

        return contextlib.suppress(Exception)
