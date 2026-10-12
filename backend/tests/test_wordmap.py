from __future__ import annotations

from vox_darija.schema import Word
from vox_darija.wordmap import align_transcript, normalize, proportional


def _ref(pairs: list[tuple[str, float, float]]) -> list[Word]:
    return [Word(word=w, start=s, end=e) for w, s, e in pairs]


def test_normalize_folds_diacritics_and_variants() -> None:
    assert normalize("شُكْراً") == normalize("شكرا")
    assert normalize("إحترام") == normalize("احترام")
    assert normalize("État,") == "etat"


def test_matched_words_inherit_reference_timings() -> None:
    ref = _ref([("شكرا", 0.0, 0.72), ("لكم", 0.72, 1.2)])
    out = align_transcript(["شكرا", "لكم"], ref, 0.0, 6.0)
    assert [(w.start, w.end) for w in out] == [(0.0, 0.72), (0.72, 1.2)]


def test_extra_words_are_interpolated_and_monotonic() -> None:
    # Whisper missed two words in the middle; they must still get sensible slots.
    ref = _ref([("شكرا", 0.0, 0.5), ("والتقدير", 3.0, 3.6)])
    out = align_transcript(["شكرا", "لكم", "كل", "والتقدير"], ref, 0.0, 4.0)

    assert [w.word for w in out] == ["شكرا", "لكم", "كل", "والتقدير"]
    assert out[0].start == 0.0 and out[-1].end == 3.6
    for a, b in zip(out, out[1:], strict=False):
        assert b.start >= a.end - 1e-9
        assert a.end > a.start  # no zero-duration words


def test_low_overlap_falls_back_to_proportional() -> None:
    ref = _ref([("xyz", 0.0, 0.5)])
    out = align_transcript(["شكرا", "لكم", "كل"], ref, 0.0, 3.0)
    plain = proportional(["شكرا", "لكم", "كل"], 0.0, 3.0)
    assert [(w.start, w.end) for w in out] == [(w.start, w.end) for w in plain]


def test_no_reference_is_proportional() -> None:
    out = align_transcript(["شكرا", "لكم"], [], 1.0, 3.0)
    assert out[0].start == 1.0 and out[-1].end == 3.0


def test_empty_input() -> None:
    assert align_transcript([], _ref([("شكرا", 0, 1)]), 0.0, 1.0) == []
