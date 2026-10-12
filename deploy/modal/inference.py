"""The GPU half: Voxtral for the transcript, Whisper for word timings.

Only this module imports torch / transformers, so the routes in ``service.py``
stay importable — and testable — on a machine with no GPU.

Two models rather than one, on purpose: Voxtral is the accurate Darija
transcriber but returns no timings, and the captions' word-sync modes depend on
timings. Whisper supplies them, and the app maps them onto Voxtral's text with
``wordmap.align_transcript`` — so a mediocre Whisper transcript cannot corrupt
the captions, only make the timings more proportional.

The aligner deliberately runs on transformers Whisper rather than
faster-whisper: CTranslate2 links against CUDA 12 (`libcublas.so.12`) while
current torch wheels bundle CUDA 13, and the two cannot be loaded together.
Staying on torch keeps the container to one CUDA stack.
"""

from __future__ import annotations

import io
import logging
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from contract import WordOut

if TYPE_CHECKING:
    import numpy as np

log = logging.getLogger("klam-asr")

SAMPLE_RATE = 16000
DEFAULT_VOXTRAL = "mistralai/Voxtral-Mini-4B-Realtime-Arabic"
DEFAULT_ALIGNER = "openai/whisper-large-v3"


@dataclass(slots=True)
class Transcript:
    text: str
    language: str | None = None
    duration: float = 0.0
    words: list[WordOut] = field(default_factory=list)
    words_source: str | None = None


def decode_wav(wav: bytes) -> np.ndarray:
    """Mono float32 at 16 kHz."""
    import numpy as np
    import soundfile as sf

    audio, rate = sf.read(io.BytesIO(wav), dtype="float32", always_2d=True)
    mono = audio.mean(axis=1) if audio.ndim > 1 else audio
    if rate != SAMPLE_RATE:
        # The app always sends 16 kHz; this is only a safety net.
        count = int(round(mono.shape[0] * SAMPLE_RATE / rate))
        mono = np.interp(
            np.linspace(0.0, 1.0, count, endpoint=False),
            np.linspace(0.0, 1.0, mono.shape[0], endpoint=False),
            mono,
        ).astype(np.float32)
    return mono.astype(np.float32)


class VoxtralEngine:
    model_id: str

    def __init__(
        self,
        model_id: str | None = None,
        aligner_id: str | None = None,
        with_aligner: bool = True,
    ) -> None:
        import torch
        from transformers import AutoProcessor, VoxtralRealtimeForConditionalGeneration

        self.model_id = model_id or os.environ.get("VOXTRAL_MODEL_ID", DEFAULT_VOXTRAL)
        self._torch = torch
        self.device = "cuda"
        self.dtype = torch.bfloat16

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

            name = aligner_id or os.environ.get("KLAM_ALIGNER_MODEL_ID", DEFAULT_ALIGNER)
            self.aligner = pipeline(
                "automatic-speech-recognition",
                model=name,
                device=self.device,
                model_kwargs={"dtype": self.dtype},
            )
            self.words_source = f"aligner:transformers/{name}"
        log.info("loaded %s (aligner=%s)", self.model_id, self.words_source)

    def _voxtral_text(self, audio) -> str:
        inputs = self.processor(audio, return_tensors="pt", sampling_rate=SAMPLE_RATE)
        inputs = inputs.to(self.device, dtype=self.dtype)
        with self._torch.inference_mode():
            generated = self.model.generate(**inputs)
        decoded = self.processor.batch_decode(generated, skip_special_tokens=True)[0]
        return decoded.strip()

    def _words(self, audio, language: str | None) -> list[WordOut]:
        if self.aligner is None:
            return []
        # Must be a mapping, never None: the pipeline iterates it, and an
        # explicit None raises "'NoneType' object is not iterable".
        generate_kwargs: dict[str, str] = {"language": language} if language else {}
        result = self.aligner(
            audio,
            return_timestamps="word",
            generate_kwargs=generate_kwargs,
        )
        words: list[WordOut] = []
        for chunk in result.get("chunks") or ():
            text = str(chunk.get("text", "")).strip()
            span = chunk.get("timestamp") or (None, None)
            start, end = span[0], span[1]
            if text and start is not None and end is not None and end > start:
                words.append(WordOut(word=text, start=float(start), end=float(end)))
        return words

    def warmup(self) -> None:
        """Run both models once so lazy init lands in the memory snapshot.

        Fixed seed on purpose: anything randomly initialised here would be
        frozen identically into every restored container.
        """
        import numpy as np

        audio = (
            np.random.default_rng(0).standard_normal(SAMPLE_RATE * 2) * 0.01
        ).astype(np.float32)
        self._voxtral_text(audio)
        self._words(audio, "ar")

    def transcribe(
        self, wav: bytes, language: str | None, with_words: bool
    ) -> Transcript:
        audio = decode_wav(wav)
        text = self._voxtral_text(audio)
        words = self._words(audio, language) if with_words else []
        return Transcript(
            text=text,
            language=language,
            duration=len(audio) / SAMPLE_RATE,
            words=words,
            words_source=self.words_source if words else None,
        )
