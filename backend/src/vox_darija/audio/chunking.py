"""Chunking of detected speech into ~30s transcription units.

Boundaries are silence-aligned so we never cut mid-word.
"""

from __future__ import annotations

from .vad import VadConfig, detect_speech


def make_chunks(
    audio, sample_rate: int, target_duration: float = 30.0
) -> list[tuple[float, float]]:
    """Return (start, end) seconds for each transcription chunk.

    Speech islands are grouped into chunks up to ``target_duration``. An island
    longer than the target is split at the longest internal silence gap
    (discovered by lowering the VAD threshold), so boundaries fall on silence.
    """
    intervals = detect_speech(audio, sample_rate)
    if not intervals:
        return []

    # Silence gaps used to split over-long islands.
    gaps = _internal_gaps(audio, sample_rate, intervals)

    chunks: list[tuple[float, float]] = []

    for start, end in intervals:
        cur_start = start

        # Split an over-long island iteratively at its internal gaps.
        while end - cur_start > target_duration:
            split = _best_split(cur_start, end, gaps, target_duration)
            if split is not None and split > cur_start:
                chunks.append((round(cur_start, 3), round(split, 3)))
                cur_start = split
            else:
                # Fallback: split at target_duration if no gap found
                fallback = cur_start + target_duration
                chunks.append((round(cur_start, 3), round(fallback, 3)))
                cur_start = fallback

        if end > cur_start:
            chunks.append((round(cur_start, 3), round(end, 3)))

    return chunks


def _internal_gaps(
    audio, sample_rate: int, intervals: list[tuple[float, float]]
) -> list[tuple[float, float]]:
    """Find silence gaps inside each speech island using a lower threshold."""
    import numpy as np

    cfg = VadConfig(threshold=0.005, min_speech=0.0, min_silence=0.1, padding=0.0)
    frame = int(sample_rate * cfg.frame_ms / 1000)
    n_frames = len(audio) // frame
    if n_frames == 0:
        return []
    frames = audio[: n_frames * frame].reshape(n_frames, frame)
    rms = np.sqrt(np.mean(frames.astype(np.float32) ** 2, axis=1))

    gaps: list[tuple[float, float]] = []
    for s, e in intervals:
        i, j = int(s * sample_rate / frame), int(e * sample_rate / frame)
        i, j = max(0, i), min(n_frames, j)
        k = i
        while k < j:
            if rms[k] < cfg.threshold:
                a = k
                while k < j and rms[k] < cfg.threshold:
                    k += 1
                b = k
                if (b - a) * frame / sample_rate >= 0.05:
                    gaps.append((a * frame / sample_rate, b * frame / sample_rate))
            else:
                k += 1
    return gaps


def _best_split(
    start: float, end: float, gaps: list[tuple[float, float]], target: float
) -> float | None:
    """Pick the largest gap whose centre is within [target*0.6, target*1.1] of start."""
    candidates = [(gs, ge) for gs, ge in gaps if start < gs and ge < end]
    if not candidates:
        return None
    best = None
    best_size = -1.0
    for gs, ge in candidates:
        centre = (gs + ge) / 2
        if target * 0.6 <= centre - start <= target * 1.1:
            if ge - gs > best_size:
                best_size = ge - gs
                best = centre
    return best
