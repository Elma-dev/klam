"""Arabic shaping correctness via HarfBuzz (the same engine libass uses).

These assert the font produces correctly shaped Arabic (no missing glyphs,
correct contextual forms, lam-alef ligature) and that mixed-script text is
handled. A font file is required; the test is skipped if it is missing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

hb = pytest.importorskip("uharfbuzz")

FONTS_DIR = Path(__file__).resolve().parents[2] / "frontend" / "public" / "fonts"
CANDIDATES = ["Cairo-Variable.ttf", "Amiri-Regular.ttf", "NotoNaskhArabic-Variable.ttf"]

FONT = next(
    (FONTS_DIR / name for name in CANDIDATES if (FONTS_DIR / name).exists()), None
)

pytestmark = pytest.mark.skipif(FONT is None, reason="no bundled font available")


def _shape(text: str, direction: str = "rtl") -> list[int]:
    blob = hb.Blob.from_file_path(str(FONT))
    face = hb.Face(blob)
    font = hb.Font(face)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.direction = direction
    buf.script = "Arab"
    buf.language = "ar"
    hb.shape(font, buf)
    return [info.codepoint for info in buf.glyph_infos]


def test_no_missing_glyphs() -> None:
    for word in ["مرحبا", "الدارجة", "المغربية", "technologie"]:
        assert 0 not in _shape(word), f".notdef in {word!r}"


def test_lam_alef_ligature() -> None:
    # lam + alef should shape to a single ligature glyph.
    assert len(_shape("لا")) == 1


def test_contextual_joining_changes_glyphs() -> None:
    isolated = _shape("ب")[0]
    initial = _shape("بب")[0]
    assert isolated != initial, "expected different contextual forms"


def test_mixed_arabic_and_latin_has_no_missing_glyphs() -> None:
    glyphs = _shape("code switching بين الدارجة 2026")
    assert 0 not in glyphs
    assert len(glyphs) > 0
