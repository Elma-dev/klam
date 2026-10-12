from __future__ import annotations

import re

from vox_darija.export import build_ass, export_subtitles
from vox_darija.export.ass import _segment_is_rtl, _visual_order, ass_color, ass_time
from vox_darija.schema import (
    CaptionStyle,
    Direction,
    MediaInfo,
    Project,
    Segment,
    Word,
    WordMode,
)


def _project(**style_kwargs) -> Project:
    style = CaptionStyle(**style_kwargs) if style_kwargs else CaptionStyle()
    return Project(
        media=MediaInfo(filename="a.mp4", duration=5.0, width=1920, height=1080),
        language="ar",
        segments=[
            Segment(id="a", start=0.0, end=1.5, text="مرحبا بكم", dir=Direction.rtl),
            Segment(
                id="b",
                start=1.5,
                end=3.25,
                text="line one\nline two",
                dir=Direction.ltr,
            ),
        ],
        style=style,
    )


def test_ass_time() -> None:
    assert ass_time(0) == "0:00:00.00"
    assert ass_time(1.5) == "0:00:01.50"
    assert ass_time(3661.25) == "1:01:01.25"


def test_ass_color_bgr_and_alpha() -> None:
    assert ass_color("#FFFFFF", 1.0) == "&H00FFFFFF"
    assert ass_color("#FF0000", 1.0) == "&H000000FF"
    assert ass_color("#000000", 0.5) == "&H80000000"


def test_ass_structure() -> None:
    ass = build_ass(_project(), 1920, 1080, 1080)
    assert "[Script Info]" in ass
    assert "PlayResX: 1920" in ass
    assert "PlayResY: 1080" in ass
    assert "[V4+ Styles]" in ass
    assert "Style: Default,Cairo," in ass
    assert "[Events]" in ass
    assert "Dialogue: 0,0:00:00.00,0:00:01.50,Default" in ass
    assert "Dialogue: 0,0:00:01.50,0:00:03.25,Default" in ass


def test_ass_line_breaks_and_rtl() -> None:
    ass = build_ass(_project(), 1920, 1080, 1080)
    assert "\\N" in ass  # newline preserved
    assert "\u200f" in ass  # RTL mark for the Arabic segment
    assert "\u200e" in ass  # LTR mark for the Latin segment


def test_ass_scales_font_with_height() -> None:
    p = _project()
    ass_1x = build_ass(p, 1920, 1080, 1080)
    ass_2x = build_ass(p, 3840, 2160, 1080)
    assert f",{p.style.font_size:.1f}," in ass_1x
    assert f",{p.style.font_size * 2:.1f}," in ass_2x


def test_ass_box_uses_border_style_3() -> None:
    p = _project()
    p.style.background.opacity = 0.6
    ass = build_ass(p, 1920, 1080, 1080)
    style_line = next(
        line for line in ass.splitlines() if line.startswith("Style: Default")
    )
    fields = style_line.split(",")
    assert fields[15] == "3"  # BorderStyle


def test_ass_no_box_uses_border_style_1() -> None:
    p = _project()
    p.style.background.opacity = 0.0
    ass = build_ass(p, 1920, 1080, 1080)
    style_line = next(
        line for line in ass.splitlines() if line.startswith("Style: Default")
    )
    assert style_line.split(",")[15] == "1"


def test_ass_word_modes_generate_per_word_lines() -> None:
    from vox_darija.config import Settings

    p = _project()
    p.segments[0].words = [
        Word(word="مرحبا", start=0.0, end=0.5),
        Word(word="بكم", start=0.5, end=1.1),
    ]
    ass = build_ass(p, 1920, 1080, 1080)
    dialogs = [line for line in ass.splitlines() if line.startswith("Dialogue:")]
    # first segment (2 words, highlight mode) yields 2 lines; second yields 1
    assert len(dialogs) >= 3
    # Settings round-trip sanity (export path used by the API)
    assert "-->" in export_subtitles(p, "srt", Settings())


def test_export_subtitles_formats() -> None:
    from vox_darija.config import Settings

    settings = Settings()
    p = _project()
    assert "-->" in export_subtitles(p, "srt", settings)
    assert export_subtitles(p, "vtt", settings).startswith("WEBVTT")
    assert "[Script Info]" in export_subtitles(p, "ass", settings)
    assert '"segments"' in export_subtitles(p, "json", settings)


def _words_segment() -> Segment:
    """A segment whose words carry timings and whose text has a line break."""
    return Segment(
        id="w",
        start=0.0,
        end=2.0,
        text="one two\nthree four",
        dir=Direction.ltr,
        words=[
            Word(word="one", start=0.0, end=0.5),
            Word(word="two", start=0.5, end=1.0),
            Word(word="three", start=1.0, end=1.5),
            Word(word="four", start=1.5, end=2.0),
        ],
    )


def test_ass_treats_semibold_as_bold() -> None:
    """ASS only has a binary bold flag; 600 must not silently render as 400."""
    for weight, expected in ((600, "-1"), (700, "-1"), (800, "-1"), (500, "0"), (400, "0")):
        ass = build_ass(_project(font_weight=weight), 1920, 1080, 1080)
        style = next(line for line in ass.splitlines() if line.startswith("Style: Default"))
        assert style.split(",")[7] == expected, f"weight {weight}"


def test_ass_word_mode_keeps_the_editors_line_breaks() -> None:
    """Rebuilding from `words` must not lose the newlines in `text`."""
    for mode in ("highlight", "reveal"):
        p = _project()
        p.style.active_word.mode = mode
        p.segments = [_words_segment()]
        ass = build_ass(p, 1920, 1080, 1080)

        dialogues = [line for line in ass.splitlines() if line.startswith("Dialogue:")]
        assert dialogues, mode
        # The break lands between "two" and "three"...
        assert re.search(r"two\\N\S*three", ass), mode
        # ...and it is the only one.
        assert max(d.count("\\N") for d in dialogues) == 1, mode
        if mode == "highlight":
            # Every cue carries the whole caption, so every cue breaks.
            # (reveal builds up, so cues before the break legitimately have none)
            assert all(d.count("\\N") == 1 for d in dialogues), mode


def test_ass_word_mode_ignores_breaks_when_words_do_not_match_text() -> None:
    """Edited text can desync from `words`; fall back to no forced breaks."""
    p = _project()
    p.style.active_word.mode = "highlight"
    seg = _words_segment()
    seg.text = "totally different words here now"
    p.segments = [seg]
    ass = build_ass(p, 1920, 1080, 1080)
    dialogues = [line for line in ass.splitlines() if line.startswith("Dialogue:")]
    assert dialogues
    assert all("\\N" not in d for d in dialogues)


def test_visual_order_reverses_rtl_words() -> None:
    """libass lays override-split runs in emission order, so RTL must be emitted visually."""
    words = ["واحد", "اثنان", "ثلاثة"]
    order, _ = _visual_order(words, set(), rtl=True)
    assert [words[i] for i in order] == ["ثلاثة", "اثنان", "واحد"]


def test_visual_order_leaves_ltr_alone() -> None:
    words = ["one", "two", "three"]
    order, _ = _visual_order(words, set(), rtl=False)
    assert [words[i] for i in order] == words


def test_visual_order_keeps_code_switching_readable() -> None:
    """A French/English run inside Darija keeps its own order."""
    words = ["مرحبا", "code", "switching", "بزاف"]
    order, _ = _visual_order(words, set(), rtl=True)
    assert [words[i] for i in order] == ["بزاف", "code", "switching", "مرحبا"]


def test_visual_order_preserves_line_structure() -> None:
    words = ["واحد", "اثنان", "ثلاثة", "اربعة"]
    order, breaks = _visual_order(words, {2}, rtl=True)
    assert [words[i] for i in order] == ["اثنان", "واحد", "اربعة", "ثلاثة"]
    assert breaks == {2}  # the break still starts the second line


def test_segment_is_rtl() -> None:
    assert _segment_is_rtl(Segment(id="x", start=0, end=1, text="مرحبا", dir=Direction.rtl))
    assert not _segment_is_rtl(
        Segment(id="x", start=0, end=1, text="hello there", dir=Direction.ltr)
    )
    # Latin text with no explicit direction stays LTR
    assert not _segment_is_rtl(Segment(id="x", start=0, end=1, text="hello"))


def test_ass_highlight_emits_rtl_in_visual_order() -> None:
    p = _project()
    p.style.active_word.mode = "highlight"
    seg = _words_segment()
    seg.dir = Direction.rtl
    seg.text = "واحد اثنان ثلاثة اربعة"
    for index, word in enumerate(("واحد", "اثنان", "ثلاثة", "اربعة")):
        seg.words[index].word = word
    p.segments = [seg]

    ass = build_ass(p, 1080, 1920, 1080)
    first = next(line for line in ass.splitlines() if line.startswith("Dialogue: 0,0:00:00.00"))
    # The leftmost word on screen must be the LAST logical one.
    assert first.index("اربعة") < first.index("واحد")


def test_default_style_is_single_word_and_unboxed() -> None:
    """The starting style: one word at a time, no background box."""
    style = CaptionStyle()
    assert style.active_word.mode == WordMode.single
    assert style.background.opacity == 0.0

    p = _project()
    p.segments = [
        Segment(
            id="w",
            start=0.0,
            end=1.1,
            text="مرحبا بكم",
            dir=Direction.rtl,
            words=[
                Word(word="مرحبا", start=0.0, end=0.5),
                Word(word="بكم", start=0.5, end=1.1),
            ],
        )
    ]
    ass = build_ass(p, 1920, 1080, 1080)
    style_line = next(line for line in ass.splitlines() if line.startswith("Style: Default"))
    assert style_line.split(",")[15] == "1"  # BorderStyle 1 -> no box

    first = next(line for line in ass.splitlines() if line.startswith("Dialogue: 0,0:00:00.00"))
    assert "مرحبا" in first
    assert "بكم" not in first  # only the spoken word is shown
