"""VoxtralProvider — a remote Voxtral endpoint.

This is the non-macOS path: ``VOX_VOXTRAL_BASE_URL`` points at a served model
(vLLM, a Modal deployment, or anything speaking the OpenAI transcription shape)
and ``VOX_VOXTRAL_API_KEY`` authenticates it.

The endpoint may also return word timings (``words``, as ``verbose_json`` does).
Those come from a *different* model than ``text``, so they are handed to the
pipeline as ``ref_words`` and mapped onto ``text`` by ``wordmap.align_transcript``
— the same contract the local MLX aligner satisfies.
"""

from __future__ import annotations

import time

import httpx
import numpy as np

from ..audio.wav import to_wav_bytes
from ..config import Settings
from ..schema import Word
from .base import ASRResult

# A serverless GPU endpoint that has scaled to zero drops the request that wakes
# it (the container is still booting), so one retry is the difference between a
# finished job and a failed one. Client errors are never retried.
_RETRY_STATUS = {500, 502, 503, 504}
_MAX_ATTEMPTS = 3


class VoxtralProvider:
    name = "voxtral"

    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        self.settings = settings
        self._client = client

    def transcribe(self, audio: np.ndarray, sample_rate: int, language: str) -> str:
        return self.transcribe_result(audio, sample_rate, language).text

    def transcribe_result(
        self, audio: np.ndarray, sample_rate: int, language: str
    ) -> ASRResult:
        base = self.settings.voxtral_base_url
        if not base:
            if self.settings.voxtral_model_id:
                raise NotImplementedError(
                    "Local Transformers Voxtral is not implemented; serve the "
                    "model and point VOX_VOXTRAL_BASE_URL at it instead."
                )
            raise RuntimeError(
                "VoxtralProvider needs VOX_VOXTRAL_BASE_URL or VOX_VOXTRAL_MODEL_ID"
            )
        return self._via_http(audio, sample_rate, language, base)

    def _via_http(self, audio, sample_rate, language, base) -> ASRResult:
        url = f"{base.rstrip('/')}/v1/audio/transcriptions"
        data: dict[str, str] = {
            "model": self.settings.voxtral_model_id or "voxtral",
            "response_format": "json",
        }
        if language and language != "auto":
            data["language"] = language
        if self.settings.timed_alignment:
            # Only ask for the aligner pass when we actually want word timings —
            # it roughly doubles the work the endpoint does per chunk.
            data["response_format"] = "verbose_json"
            data["word_timestamps"] = "true"

        headers: dict[str, str] = {}
        if self.settings.voxtral_api_key:
            headers["Authorization"] = f"Bearer {self.settings.voxtral_api_key}"

        resp = self._post_with_retry(
            url,
            # A real RIFF WAV, not bare samples behind a .wav filename.
            files={"file": ("audio.wav", to_wav_bytes(audio, sample_rate), "audio/wav")},
            data=data,
            headers=headers,
        )
        payload = resp.json()
        return ASRResult(
            text=(payload.get("text") or "").strip(),
            ref_words=parse_words(payload.get("words")),
        )

    def _post_with_retry(self, url: str, **kwargs) -> httpx.Response:
        """POST, retrying the failures a cold serverless endpoint produces."""
        last: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            if attempt:
                time.sleep(min(2**attempt, 5))
            try:
                resp = self._client_or_new().post(
                    url, timeout=self.settings.voxtral_timeout, **kwargs
                )
            except httpx.TransportError as exc:
                last = exc
                continue
            if resp.status_code in _RETRY_STATUS:
                last = httpx.HTTPStatusError(
                    f"endpoint returned {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )
                continue
            resp.raise_for_status()
            return resp
        assert last is not None
        raise last

    def _client_or_new(self) -> httpx.Client:
        """Reuse one pool across the chunks of a job."""
        if self._client is None:
            self._client = httpx.Client()
        return self._client


def parse_words(raw) -> list[Word] | None:
    """Read an OpenAI-style ``words`` array, ignoring malformed entries."""
    if not raw:
        return None
    words: list[Word] = []
    for item in raw:
        try:
            text = str(item["word"]).strip()
            start = float(item["start"])
            end = float(item["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if text and end > start:
            words.append(Word(word=text, start=start, end=end))
    return words or None
