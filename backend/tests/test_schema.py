from __future__ import annotations

from vox_darija.schema import CaptionStyle, Project, Segment


def test_segment_roundtrip() -> None:
    seg = Segment(id="a1", start=0.0, end=1.5, text="مرحبا بكم")
    assert seg.model_dump()["text"] == "مرحبا بكم"


def test_project_roundtrip() -> None:
    from vox_darija.schema import MediaInfo

    p = Project(
        media=MediaInfo(filename="a.mp4", duration=10.0, width=1920, height=1080),
        segments=[Segment(id="a1", start=0.0, end=2.0, text="مرحبا")],
    )
    data = p.model_dump_json()
    p2 = Project.model_validate_json(data)
    assert p2.segments[0].text == "مرحبا"
    assert p2.style.font_family == "Cairo"


def test_default_style_is_rtl_ready() -> None:
    style = CaptionStyle()
    assert style.direction.value == "auto"
