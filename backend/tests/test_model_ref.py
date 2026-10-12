"""Model reference resolution (local directory vs HuggingFace repo id)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vox_darija.model_ref import resolve_mlx_model


def test_repo_id_is_passed_through() -> None:
    # mlx-audio downloads these, so they must not be mistaken for paths.
    ref = "mistralai/Voxtral-Mini-4B-Realtime-Arabic"
    assert resolve_mlx_model(ref, what="ASR") == ref


def test_existing_directory_is_resolved(tmp_path: Path) -> None:
    (tmp_path / "model").mkdir()
    resolved = resolve_mlx_model(str(tmp_path / "model"), what="ASR")
    assert Path(resolved).is_dir()


def test_tilde_is_expanded_for_an_existing_directory(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / "models" / "x").mkdir(parents=True)
    assert resolve_mlx_model("~/models/x", what="ASR") == str(tmp_path / "models" / "x")


@pytest.mark.parametrize("ref", ["~/models/nope", "./nope", "/definitely/not/here"])
def test_missing_path_names_the_fix(ref: str) -> None:
    # The whole point of the check: a fresh clone should be told what to run,
    # not handed a bare path error.
    with pytest.raises(FileNotFoundError) as excinfo:
        resolve_mlx_model(ref, what="ASR")
    assert "make model" in str(excinfo.value)


def test_relative_name_is_treated_as_a_repo_id_like_mlx_audio_does() -> None:
    # mlx-audio's own heuristic only treats . / ~ and drive letters as paths;
    # anything else is a repo id. Agreeing with it avoids a false "not found".
    assert resolve_mlx_model("some-org/some-model", what="ASR") == "some-org/some-model"
