from __future__ import annotations

import io
import wave

import numpy as np

from klam.audio.wav import to_wav_bytes, write_wav


def test_to_wav_bytes_is_a_real_wav() -> None:
    data = to_wav_bytes(np.zeros(1600, dtype=np.float32), 16000)
    assert data[:4] == b"RIFF"
    assert data[8:12] == b"WAVE"


def test_to_wav_bytes_round_trips() -> None:
    audio = (np.sin(np.linspace(0, 20, 1600)) * 0.5).astype(np.float32)
    with wave.open(io.BytesIO(to_wav_bytes(audio, 16000)), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 16000
        assert wf.getnframes() == 1600


def test_write_wav_produces_a_readable_file(tmp_path) -> None:
    path = str(tmp_path / "clip.wav")
    write_wav(path, np.zeros(800, dtype=np.float32), 16000)
    with wave.open(path, "rb") as wf:
        assert wf.getnframes() == 800
        assert wf.getframerate() == 16000


def test_samples_are_clipped_not_wrapped() -> None:
    """Out-of-range input must saturate — scaling 2.0 by 32767 would wrap negative."""
    loud = np.array([2.0, -2.0, 0.0], dtype=np.float32)
    with wave.open(io.BytesIO(to_wav_bytes(loud, 16000)), "rb") as wf:
        samples = np.frombuffer(wf.readframes(3), dtype=np.int16)
    assert samples[0] == 32767
    assert samples[1] == -32767
    assert samples[2] == 0
