# Klam — backend

FastAPI + Python backend for the Klam auto-captioning editor. See the
root `README.md` and `docs/PLAN.md` for the full picture.

Quickstart (from the backend directory):

```bash
uv venv .venv
uv pip install -e ".[dev]"        # core + tests (no MLX)
uv pip install -e ".[dev,mlx]"    # + MLX provider for macOS
uv run klam transcribe video.mp4 --lang ar --format srt
uv run uvicorn klam.main:app --reload
```
