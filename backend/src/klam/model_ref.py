"""Resolve a model reference into something ``mlx_audio`` can load.

``mlx_audio.stt.load()`` accepts either a local directory or a HuggingFace repo
id, and downloads the latter on first use. So the only case worth handling here
is a local-looking path that is missing: catching it lets a fresh clone fail
with the command that fixes it, instead of a bare path error or a Hub 404.
"""

from __future__ import annotations

from pathlib import Path


def _looks_like_path(ref: str) -> bool:
    """Mirrors mlx_audio's own heuristic, so we agree on what a path is.

    Anything not matching stays a repo id, which is the common case for the
    defaults.
    """
    return ref.startswith((".", "/", "~")) or (len(ref) > 1 and ref[1] == ":")


def resolve_mlx_model(ref: str, *, what: str) -> str:
    """Return a value ``mlx_audio.stt.load()`` accepts.

    An existing directory is returned expanded, which is what lets an offline
    machine point at a local conversion. Anything else is passed through for
    mlx-audio to fetch from the Hub.
    """
    path = Path(ref).expanduser()
    if path.is_dir():
        return str(path)
    if not _looks_like_path(ref):
        return ref
    raise FileNotFoundError(
        f"{what} model not found at {path}.\n"
        "Build the default 8-bit MLX model with `make model`, or point "
        "KLAM_MLX_MODEL at a model on the Hugging Face Hub."
    )
