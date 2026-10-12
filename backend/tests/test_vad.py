from __future__ import annotations

import numpy as np

from vox_darija.audio.vad import VadConfig, detect_speech


def _tone(freq: float, dur: float, sr: int = 16000, amp: float = 0.3) -> np.ndarray:
    t = np.arange(int(dur * sr)) / sr
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _audio() -> np.ndarray:
    sr = 16000
    return np.concatenate(
        [
            np.zeros(int(0.5 * sr), dtype=np.float32),  # leading silence
            _tone(440, 1.0),
            np.zeros(int(0.6 * sr), dtype=np.float32),  # gap
            _tone(880, 1.0),
            np.zeros(int(0.5 * sr), dtype=np.float32),  # trailing silence
        ]
    )


def test_detect_two_speech_islands() -> None:
    sr = 16000
    intervals = detect_speech(_audio(), sr)
    assert len(intervals) == 2
    # First island starts near 0.5s, ends near 1.5s
    assert abs(intervals[0][0] - 0.5) < 0.25
    assert abs(intervals[0][1] - 1.5) < 0.25


def test_silent_audio_has_no_speech() -> None:
    sr = 16000
    silent = np.zeros(int(2 * sr), dtype=np.float32)
    assert detect_speech(silent, sr) == []


def test_min_speech_drops_short_bursts() -> None:
    sr = 16000
    audio = np.concatenate(
        [np.zeros(int(0.2 * sr)), _tone(440, 0.1), np.zeros(int(0.2 * sr))]
    ).astype(np.float32)
    cfg = VadConfig(min_speech=0.25)
    assert detect_speech(audio, sr, cfg) == []
