"""Filesystem path resolution (fonts, data)."""

from __future__ import annotations

from pathlib import Path

from .config import Settings


def _candidates(settings: Settings) -> list[Path]:
    here = Path(__file__).resolve()
    repo = here.parents[3]  # .../backend/src/vox_darija -> repo root
    out: list[Path] = []
    if settings.fonts_dir:
        out.append(Path(settings.fonts_dir).expanduser())
    out.append(repo / "frontend" / "public" / "fonts")
    out.append(Path("../frontend/public/fonts"))
    out.append(Path("frontend/public/fonts"))
    return out


def resolve_fonts_dir(settings: Settings) -> Path | None:
    for path in _candidates(settings):
        if path.is_dir():
            return path.resolve()
    return None
