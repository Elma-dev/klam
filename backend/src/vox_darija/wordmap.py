"""Transfer word timings from a reference transcript onto another transcript.

The ASR we caption (Voxtral) returns text only; Whisper supplies word
boundaries for the same audio. The two transcripts disagree on spelling and
sometimes on the words themselves, so the reference words are matched to the
target words by sequence alignment: matched words inherit the reference timing,
and the runs the two disagree on are filled in proportionally to character count
between the surrounding matched anchors.
"""

from __future__ import annotations

import difflib
import unicodedata
from collections.abc import Sequence

from .schema import Word

# Fold Arabic orthographic variants so close spellings still match.
_FOLD = str.maketrans(
    {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ى": "ي",
        "ئ": "ي",
        "ؤ": "و",
        "ة": "ه",
        "ـ": "",
    }
)


def normalize(token: str) -> str:
    """Return a comparison key for a word (case/punctuation/diacritics folded)."""
    text = unicodedata.normalize("NFKD", token).lower()
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.translate(_FOLD)
    return "".join(ch for ch in text if ch.isalnum())


def proportional(words: Sequence[str], start: float, end: float) -> list[Word]:
    """Distribute ``words`` across ``[start, end]`` by character count."""
    if not words:
        return []
    total = sum(len(w) for w in words) or 1
    span = max(0.0, end - start)
    out: list[Word] = []
    cursor = start
    for i, word in enumerate(words):
        w_end = end if i == len(words) - 1 else cursor + span * (len(word) / total)
        if w_end <= cursor:
            w_end = cursor + 0.001
        out.append(Word(word=word, start=round(cursor, 3), end=round(w_end, 3)))
        cursor = w_end
    return out


def _anchors(hyp: Sequence[str], ref: Sequence[Word]) -> tuple[list[tuple[float, float] | None], int]:
    """Match hyp words to ref words; return per-hyp timing (or None) and match count."""
    key_hyp = [normalize(w) for w in hyp]
    key_ref = [normalize(w.word) for w in ref]

    slots: list[tuple[float, float] | None] = [None] * len(hyp)
    matched = 0
    matcher = difflib.SequenceMatcher(a=key_hyp, b=key_ref, autojunk=False)
    for i, j, size in matcher.get_matching_blocks():
        for d in range(size):
            if key_hyp[i + d]:
                slots[i + d] = (ref[j + d].start, ref[j + d].end)
                matched += 1
    return slots, matched


def align_transcript(
    hyp_words: Sequence[str],
    ref: Sequence[Word],
    start: float,
    end: float,
    min_duration: float = 0.08,
) -> list[Word]:
    """Give ``hyp_words`` timings, borrowing from ``ref`` where they agree.

    Falls back to a pure proportional spread over ``[start, end]`` when there is
    no reference or too little overlap to trust the matches.
    """
    words = list(hyp_words)
    if not words:
        return []
    if not ref:
        return proportional(words, start, end)

    slots, matched = _anchors(words, ref)
    if matched < max(1, int(0.3 * len(words))):
        return proportional(words, start, end)

    key_len = [max(1, len(normalize(w))) for w in words]

    # Fill each run of unmatched words proportionally between its neighbours.
    i = 0
    while i < len(words):
        if slots[i] is not None:
            i += 1
            continue
        j = i
        while j < len(words) and slots[j] is None:
            j += 1

        gap_start = start if i == 0 else slots[i - 1][1]  # type: ignore[index]
        gap_end = end if j == len(words) else slots[j][0]  # type: ignore[index]
        if gap_end <= gap_start:
            gap_end = gap_start + 0.001 * (j - i)

        span = gap_end - gap_start
        total = sum(key_len[i:j])
        cursor = gap_start
        for k in range(i, j):
            fill_end = gap_end if k == j - 1 else cursor + span * (key_len[k] / total)
            slots[k] = (cursor, fill_end)
            cursor = fill_end
        i = j

    # Enforce monotonic, non-zero durations.
    out: list[Word] = []
    prev_end = start
    for word, slot in zip(words, slots, strict=True):
        assert slot is not None
        s = max(slot[0], prev_end)
        e = max(slot[1], s + min_duration)
        out.append(Word(word=word, start=round(s, 3), end=round(e, 3)))
        prev_end = e
    return out
