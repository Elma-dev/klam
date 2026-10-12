from __future__ import annotations

from klam.schema import Word
from klam.segmentation import (
    SegmentConfig,
    segment_chunks,
    segment_words,
    split_sentences,
)


def test_split_sentences_arabic_and_latin_punctuation() -> None:
    text = "مرحبا بكم. كيف حالكم؟ جيد!"
    parts = split_sentences(text)
    assert parts == ["مرحبا بكم.", "كيف حالكم؟", "جيد!"]


def test_split_sentences_code_switched() -> None:
    text = "هاد الفيديو مهم. This is important, vraiment!"
    parts = split_sentences(text)
    assert len(parts) >= 2


def test_segment_chunks_assigns_monotonic_times() -> None:
    chunks = [(0.0, 6.0, "مرحبا بكم في الدارجة. اليوم غادي نتكلمو على التكنولوجيا.")]
    segs = segment_chunks(chunks, SegmentConfig())
    assert segs
    prev_end = segs[0].start
    for s in segs:
        assert s.end >= s.start
        assert s.start >= prev_end - 1e-6
        prev_end = s.end
    assert abs(segs[-1].end - 6.0) < 1e-6
    assert abs(segs[0].start - 0.0) < 1e-6


def test_lines_respect_max_chars() -> None:
    cfg = SegmentConfig(max_chars_per_line=10, max_lines=2, max_duration=100.0)
    chunks = [(0.0, 5.0, "word word word word word word")]
    segs = segment_chunks(chunks, cfg)
    for s in segs:
        for line in s.text.split("\n"):
            assert len(line) <= 10 or len(line.split()) == 1


def test_segment_words_uses_word_times() -> None:
    words = [
        Word(word="مرحبا", start=0.0, end=0.4),
        Word(word="بكم.", start=0.4, end=0.9),
        Word(word="كيف", start=3.5, end=3.8),  # long pause before
        Word(word="حالكم؟", start=3.8, end=4.3),
    ]
    segs = segment_words(words, SegmentConfig())
    # Sentence punctuation and the 2.6 s pause each force a new caption.
    assert len(segs) == 2
    assert segs[0].start == 0.0 and segs[0].end == 0.9
    assert segs[1].start == 3.5
    assert [w.word for w in (segs[0].words or [])] == ["مرحبا", "بكم."]


def test_segment_words_respects_line_budget() -> None:
    cfg = SegmentConfig(max_chars_per_line=8, max_lines=1, max_duration=100.0)
    words = [
        Word(word=w, start=i * 0.3, end=i * 0.3 + 0.3)
        for i, w in enumerate("aaa bbb ccc ddd".split())
    ]
    segs = segment_words(words, cfg)
    assert len(segs) == 2
    for s in segs:
        assert len(s.text.split("\n")) <= 1
