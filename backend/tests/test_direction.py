from __future__ import annotations

from klam.direction import detect_direction, has_rtl


def test_arabic_is_rtl() -> None:
    assert detect_direction("مرحبا بكم في الدارجة") == "rtl"


def test_latin_is_ltr() -> None:
    assert detect_direction("hello world") == "ltr"


def test_first_strong_character_wins() -> None:
    # Leading punctuation/numerals are neutral; first strong char decides.
    assert detect_direction("123 hello") == "ltr"
    assert detect_direction("123 مرحبا") == "rtl"
    assert detect_direction("«مرحبا»") == "rtl"


def test_code_switched_darija_starts_rtl() -> None:
    assert detect_direction("واش هاد الفيديو مهم؟") == "rtl"
    assert detect_direction("code switching بين الدارجة والفرنسية") == "ltr"


def test_empty_and_neutral_default_ltr() -> None:
    assert detect_direction("") == "ltr"
    assert detect_direction("123 456 !!!") == "ltr"


def test_has_rtl() -> None:
    assert has_rtl("hello مرحبا") is True
    assert has_rtl("hello") is False
