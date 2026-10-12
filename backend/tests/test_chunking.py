from __future__ import annotations

import numpy as np

from klam.audio.chunking import make_chunks


def _tone(freq: float, dur: float, sr: int = 16000, amp: float = 0.3) -> np.ndarray:
    t = np.arange(int(dur * sr)) / sr
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def test_short_audio_is_one_chunk() -> None:
    sr = 16000
    audio = np.concatenate([_tone(440, 3.0), np.zeros(int(0.5 * sr), dtype=np.float32)])
    chunks = make_chunks(audio, sr, target_duration=30.0)
    assert len(chunks) == 1


def test_no_speech_no_chunks() -> None:
    sr = 16000
    audio = np.zeros(int(2 * sr), dtype=np.float32)
    assert make_chunks(audio, sr) == []


def test_long_island_split_on_silence() -> None:
    sr = 16000
    audio = np.concatenate(
        [
            _tone(440, 20.0),
            np.zeros(int(0.8 * sr), dtype=np.float32),  # silence gap
            _tone(440, 20.0),
        ]
    )
    chunks = make_chunks(audio, sr, target_duration=30.0)
    # 40s of speech with a gap should produce 2 chunks, split at the gap.
    assert len(chunks) == 2
    # boundaries within +/-1s of the 20s gap centre
    for start, end in chunks:
        assert end > start
    assert abs(chunks[0][1] - 20.0) < 1.0


def _tone(freq, dur, sr=16000, amp=0.3):
    t = np.arange(int(dur * sr)) / sr
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def test_disjoint_islands_are_separate():
    sr = 16000
    # 2s speech, 5s silence, 2s speech
    audio = np.concatenate(
        [_tone(440, 2.0), np.zeros(int(5.0 * sr), dtype=np.float32), _tone(440, 2.0)]
    )
    chunks = make_chunks(audio, sr, target_duration=30.0)
    print("Chunks:", chunks)
    assert len(chunks) == 2


if __name__ == "__main__":
    test_disjoint_islands_are_separate()
    print("Passed.")
