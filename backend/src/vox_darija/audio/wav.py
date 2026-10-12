"""WAV encoding, shared by providers that hand audio to a model or an API.

Bare int16 samples written into a file named ``.wav`` are *not* a WAV file —
anything that parses it as RIFF (a model server, an HTTP endpoint) fails or
misreads it. Encode properly, in one place.
"""

from __future__ import annotations

import io
import wave

import numpy as np

_SAMPLE_WIDTH = 2  # 16-bit


def _pcm16(audio: np.ndarray) -> bytes:
    return (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16).tobytes()


def to_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    """Mono 16-bit WAV bytes, RIFF header included."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(_SAMPLE_WIDTH)
        wf.setframerate(sample_rate)
        wf.writeframes(_pcm16(audio))
    return buf.getvalue()


def write_wav(path: str, audio: np.ndarray, sample_rate: int) -> None:
    """Write mono 16-bit WAV to ``path``."""
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(_SAMPLE_WIDTH)
        wf.setframerate(sample_rate)
        wf.writeframes(_pcm16(audio))
