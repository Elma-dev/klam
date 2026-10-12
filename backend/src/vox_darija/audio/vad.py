"""Voice activity detection (energy-based, deterministic, dependency-free).

A simple RMS-threshold VAD with hysteresis. Good enough for chunk boundary
placement; swap in Silero VAD later without changing the interface.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VadConfig:
    frame_ms: int = 30
    threshold: float = 0.02  # RMS threshold in [-1, 1]
    min_speech: float = 0.25  # seconds: drop shorter speech islands
    min_silence: float = 0.4  # seconds: silence gap that ends a speech island
    padding: float = 0.15  # seconds added around each detected island


def detect_speech(
    audio, sample_rate: int, config: VadConfig | None = None
) -> list[tuple[float, float]]:
    """Return speech intervals as (start, end) in seconds."""
    import numpy as np

    cfg = config or VadConfig()
    frame = max(1, int(sample_rate * cfg.frame_ms / 1000))
    n_frames = len(audio) // frame
    if n_frames == 0:
        return []

    frames = audio[: n_frames * frame].reshape(n_frames, frame)
    rms = np.sqrt(np.mean(frames.astype(np.float32) ** 2, axis=1))

    min_speech_frames = max(1, int(cfg.min_speech * 1000 / cfg.frame_ms))
    min_silence_frames = max(1, int(cfg.min_silence * 1000 / cfg.frame_ms))

    intervals: list[tuple[int, int]] = []
    i = 0
    while i < n_frames:
        if rms[i] >= cfg.threshold:
            start = i
            j = i
            while j < n_frames and rms[j] >= cfg.threshold:
                j += 1
            end = j
            # extend through trailing silence shorter than min_silence
            k = end
            silent = 0
            while k < n_frames and silent < min_silence_frames:
                if rms[k] < cfg.threshold:
                    silent += 1
                else:
                    silent = 0
                    end = k + 1
                k += 1
            if (end - start) >= min_speech_frames:
                intervals.append((start, end))
            i = end + 1
        else:
            i += 1

    pad_frames = int(cfg.padding * 1000 / cfg.frame_ms)
    result: list[tuple[float, float]] = []
    for start, end in intervals:
        s = max(0, start - pad_frames)
        e = min(n_frames, end + pad_frames)
        result.append((s * frame / sample_rate, e * frame / sample_rate))
    return result
