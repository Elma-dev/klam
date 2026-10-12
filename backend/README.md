# Vox Darija — backend

FastAPI + Python backend for the Vox Darija auto-captioning editor. See the
root `README.md` and `docs/PLAN.md` for the full picture.

Quickstart (from the backend directory):

```bash
uv venv .venv
uv pip install -e ".[dev]"        # core + tests (no MLX)
uv pip install -e ".[dev,mlx]"    # + MLX provider for macOS
uv run vox-darija transcribe video.mp4 --lang ar --format srt
uv run uvicorn vox_darija.main:app --reload
```
