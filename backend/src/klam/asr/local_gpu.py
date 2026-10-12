"""LocalGPUProvider — Voxtral plus Whisper, in-process on a CUDA GPU.

The non-Apple counterpart to ``MLXAudioProvider``: Voxtral (Arabic) supplies the
transcript, transformers Whisper supplies word timings, and the pipeline merges
them with ``wordmap.align_transcript`` — the same contract the remote provider
and the MLX aligner satisfy.

Torch and transformers are imported lazily so the package still installs and
imports without them.
"""

from __future__ import annotations

import numpy as np

from ..schema import Word
from .base import ASRResult

DEFAULT_VOXTRAL = "mistralai/Voxtral-Mini-4B-Realtime-Arabic"
DEFAULT_ALIGNER = "openai/whisper-large-v3-turbo"


class LocalGPUProvider:
    name = "local-gpu"

    def __init__(
        self,
        model_id: str | None = None,
        aligner_id: str | None = None,
        with_aligner: bool = True,
    ) -> None:
        import torch
        from transformers import AutoProcessor, VoxtralRealtimeForConditionalGeneration

        self.model_id = model_id or DEFAULT_VOXTRAL
        self._torch = torch
        # Never hardcode "cuda": ZeroGPU's emulation and CPU-only hosts both need
        # the probe, and the decorator is a no-op off ZeroGPU.
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.dtype = torch.bfloat16 if self.device == "cuda" else torch.float32

        self.processor = AutoProcessor.from_pretrained(self.model_id)
        self.model = (
            VoxtralRealtimeForConditionalGeneration.from_pretrained(
                self.model_id, dtype=self.dtype
            )
            .to(self.device)
            .eval()
        )

        self.aligner = None
        self.words_source: str | None = None
        if with_aligner:
            from transformers import pipeline

            name = aligner_id or DEFAULT_ALIGNER
            self.aligner = pipeline(
                "automatic-speech-recognition",
                model=name,
                device=self.device,
                model_kwargs={"dtype": self.dtype},
            )
            self.words_source = f"aligner:transformers/{name}"

    def _text(self, audio: np.ndarray) -> str:
        inputs = self.processor(audio, return_tensors="pt", sampling_rate=16000)
        inputs = inputs.to(self.device, dtype=self.dtype)
        with self._torch.inference_mode():
            generated = self.model.generate(**inputs)
        return self.processor.batch_decode(generated, skip_special_tokens=True)[0].strip()

    def _words(self, audio: np.ndarray, language: str | None) -> list[Word]:
        if self.aligner is None:
            return []
        # The pipeline falls back to settings.language, which is the sentinel
        # "auto" — Whisper rejects that outright ("Unsupported language: auto"),
        # so it must become "no language given" rather than being forwarded.
        lang = None if language in (None, "", "auto") else language
        # Must be a mapping, never None: the pipeline iterates it, and an
        # explicit None raises "'NoneType' object is not iterable".
        generate_kwargs: dict[str, str] = {"language": lang} if lang else {}
        result = self.aligner(
            audio, return_timestamps="word", generate_kwargs=generate_kwargs
        )
        words: list[Word] = []
        for chunk in result.get("chunks") or ():
            text = str(chunk.get("text", "")).strip()
            span = chunk.get("timestamp") or (None, None)
            start, end = span[0], span[1]
            if text and start is not None and end is not None and end > start:
                words.append(Word(word=text, start=float(start), end=float(end)))
        return words

    def warmup(self) -> None:
        """Run both models once so lazy init lands in a ZeroGPU memory snapshot.

        Fixed seed on purpose: anything randomly initialised here would be frozen
        identically into every restored container.
        """
        audio = (
            np.random.default_rng(0).standard_normal(16000 * 2) * 0.01
        ).astype(np.float32)
        self._text(audio)
        self._words(audio, "ar")

    def transcribe(self, audio: np.ndarray, sample_rate: int, language: str) -> str:
        return self.transcribe_result(audio, sample_rate, language).text

    def transcribe_result(
        self, audio: np.ndarray, sample_rate: int, language: str
    ) -> ASRResult:
        """Transcript plus reference word timings (from a different model)."""
        text = self._text(audio)
        return ASRResult(text=text, ref_words=self._words(audio, language))
