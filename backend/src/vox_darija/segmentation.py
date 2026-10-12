"""Caption segmentation rules.

Turns chunk-level text into timed caption ``Segment`` objects, wrapping lines
(newlines are preserved in ``text``), capping line count and duration, and
splitting on sentence punctuation.
"""

from __future__ import annotations

import math
import re
import uuid
from dataclasses import dataclass

from .direction import detect_direction
from .schema import Direction, Segment, Word

_SENTENCE_RE = re.compile(r"(?<=[.!?؟،۔])\s+|\n+")


@dataclass(frozen=True)
class SegmentConfig:
    max_chars_per_line: int = 42
    max_lines: int = 2
    max_duration: float = 7.0


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_RE.split(text) if s.strip()]


def _wrap_lines(words: list[str], max_chars: int) -> list[str]:
    """Pack words into lines of <= max_chars (whole words only)."""
    lines: list[str] = []
    current: list[str] = []
    current_len = 0
    for word in words:
        add = len(word) + (1 if current else 0)
        if current and current_len + add > max_chars:
            lines.append(" ".join(current))
            current = []
            current_len = 0
            add = len(word)
        current.append(word)
        current_len += add
    if current:
        lines.append(" ".join(current))
    return lines


def _words_to_captions(
    words: list[str], start: float, end: float, cfg: SegmentConfig
) -> list[Segment]:
    """Split a word list into captions honoring duration/line limits, with
    time distributed proportionally to character count."""
    if not words:
        return []

    span = end - start
    # Split into duration-bounded word groups (proportional by char count).
    groups: list[list[str]] = []
    if span > cfg.max_duration:
        # Aim for enough groups to meet max_duration, but never create
        # captions shorter than ~3 words (avoids one-word captions when a
        # short transcript spans a long chunk).
        n = max(2, int(span / cfg.max_duration) + 1)
        n = min(n, max(1, len(words) // 3))
        if n > 1:
            step = math.ceil(len(words) / n)
            groups = [words[i : i + step] for i in range(0, len(words), step)]
        else:
            groups = [words]
    else:
        groups = [words]

    # Ensure no group produces more than max_lines lines; split by lines.
    final: list[list[str]] = []
    for group in groups:
        lines = _wrap_lines(group, cfg.max_chars_per_line)
        for i in range(0, len(lines), cfg.max_lines):
            final.append(" ".join(lines[i : i + cfg.max_lines]).split())

    total_chars = sum(len(w) for w in words) or 1
    out: list[Segment] = []
    cursor = start
    acc = 0
    for i, group in enumerate(final):
        acc += sum(len(w) for w in group)
        g_end = end if i == len(final) - 1 else start + span * (acc / total_chars)
        text = "\n".join(_wrap_lines(group, cfg.max_chars_per_line))
        out.append(_make_segment(text, cursor, g_end))
        cursor = g_end
    return out


def _segment_sentence(
    text: str, start: float, end: float, cfg: SegmentConfig
) -> list[Segment]:
    return _words_to_captions(text.split(), start, end, cfg)


def _make_segment(text: str, start: float, end: float) -> Segment:
    return Segment(
        id=uuid.uuid4().hex[:12],
        start=round(start, 3),
        end=round(end, 3),
        text=text,
        dir=Direction(detect_direction(text)),
    )


_SENT_END = re.compile(r"[.!?؟۔]$")


def segment_words(words: list[Word], cfg: SegmentConfig | None = None) -> list[Segment]:
    """Build caption segments from word-level timings.

    Captions break on sentence punctuation, long pauses, max duration, and the
    line/character budget. Timings come straight from the words, so captions
    follow the voice.
    """
    cfg = cfg or SegmentConfig()
    if not words:
        return []

    out: list[Segment] = []
    current: list[Word] = []

    def flush() -> None:
        if not current:
            return
        text = "\n".join(_wrap_lines([w.word for w in current], cfg.max_chars_per_line))
        out.append(
            Segment(
                id=uuid.uuid4().hex[:12],
                start=round(current[0].start, 3),
                end=round(current[-1].end, 3),
                text=text,
                dir=Direction(detect_direction(text)),
                words=[Word(word=w.word, start=w.start, end=w.end) for w in current],
            )
        )

    for word in words:
        if current:
            gap = word.start - current[-1].end
            over_duration = word.end - current[0].start > cfg.max_duration
            if gap > 0.7 or over_duration or _SENT_END.search(current[-1].word):
                flush()
                current = []
        current.append(word)
        lines = _wrap_lines([w.word for w in current], cfg.max_chars_per_line)
        if len(lines) > cfg.max_lines and len(current) > 1:
            current.pop()
            flush()
            current = [word]
    flush()
    return out


def segment_chunks(
    chunks: list[tuple[float, float, str]], cfg: SegmentConfig | None = None
) -> list[Segment]:
    """Convert (start, end, text) chunk triples into caption segments."""
    cfg = cfg or SegmentConfig()
    out: list[Segment] = []
    for start, end, text in chunks:
        sentences = split_sentences(text)
        if not sentences:
            continue
        total_chars = sum(len(s) for s in sentences) or 1
        cursor = start
        acc = 0.0
        for i, sent in enumerate(sentences):
            s = cursor
            acc += len(sent)
            e = (
                end
                if i == len(sentences) - 1
                else start + (end - start) * (acc / total_chars)
            )
            out.extend(_segment_sentence(sent, s, e, cfg))
            cursor = e
    return out
