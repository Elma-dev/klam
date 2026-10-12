"""Shared caption + style JSON schema.

This is the single source of truth consumed by the browser preview, the ASS
generator, and project save/load. It is validated with Pydantic here and
mirrored with Zod in the frontend.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.0.0"


class Language(StrEnum):
    auto = "auto"
    ar = "ar"
    fr = "fr"
    en = "en"


class Direction(StrEnum):
    auto = "auto"
    ltr = "ltr"
    rtl = "rtl"


class Alignment(StrEnum):
    left = "left"
    center = "center"
    right = "right"


class VerticalPosition(StrEnum):
    top = "top"
    middle = "middle"
    bottom = "bottom"


class AnimationType(StrEnum):
    none = "none"
    fade = "fade"
    pop = "pop"
    slide = "slide"


class Word(BaseModel):
    word: str
    start: float
    end: float


class Segment(BaseModel):
    id: str
    start: float
    end: float
    text: str
    words: list[Word] | None = None
    speaker: str | None = None
    dir: Direction | None = None


class Outline(BaseModel):
    color: str = "#000000"
    width: float = 0.0


class Shadow(BaseModel):
    color: str = "#000000"
    offset_x: float = 0.0
    offset_y: float = 2.0
    blur: float = 0.0
    opacity: float = 0.5


class Background(BaseModel):
    color: str = "#000000"
    opacity: float = 0.0
    padding: float = 20.0
    radius: float = 8.0


class Position(BaseModel):
    vertical: VerticalPosition = VerticalPosition.bottom
    # Fractional offsets (0..1) relative to video width/height. None = centered.
    x: float | None = None
    y: float | None = None


class WordMode(StrEnum):
    highlight = "highlight"
    reveal = "reveal"
    single = "single"


class ActiveWord(BaseModel):
    color: str = "#FFE900"
    scale: float = 1.15
    mode: WordMode = WordMode.single


class Animation(BaseModel):
    type: AnimationType = AnimationType.none
    duration: float = 0.25


class CaptionStyle(BaseModel):
    font_family: str = "Cairo"
    font_size: float = 48.0
    font_weight: int = 600
    italic: bool = False
    color: str = "#FFFFFF"
    outline: Outline = Field(default_factory=Outline)
    shadow: Shadow = Field(default_factory=Shadow)
    background: Background = Field(default_factory=Background)
    position: Position = Field(default_factory=Position)
    align: Alignment = Alignment.center
    line_spacing: float = 1.2
    margin_h: float = 40.0
    margin_v: float = 40.0
    direction: Direction = Direction.auto
    active_word: ActiveWord = Field(default_factory=ActiveWord)
    animation: Animation = Field(default_factory=Animation)


class StylePreset(BaseModel):
    id: str
    name: str
    style: CaptionStyle


class MediaInfo(BaseModel):
    filename: str
    duration: float
    width: int
    height: int


class Project(BaseModel):
    version: str = SCHEMA_VERSION
    media: MediaInfo
    language: Language = Language.auto
    segments: list[Segment] = Field(default_factory=list)
    style: CaptionStyle = Field(default_factory=CaptionStyle)
    presets: list[StylePreset] = Field(default_factory=list)
