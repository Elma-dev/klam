# CLAUDE.md

Guidance for AI assistants working on this repository.

## What this is

Klam is an open-source auto-captioning video editor, Arabic-first. A user
uploads a video, the backend transcribes speech into timed captions, and the
frontend lets them edit text/timings and style captions, then export burned-in
MP4 / SRT / VTT / ASS. Arabic + RTL correctness is a first-class requirement.

Transcription backends are pluggable and **the app is not Apple-only**: `mlx`
(Apple Silicon, the default), `local-gpu` (torch + transformers on an NVIDIA
GPU), `voxtral` (a remote endpoint), and `mock`. Only `asr/mlx_audio.py` and
`aligners.py` are Apple-specific; everything else — pipeline, export, frontend —
is cross-platform, so do not assume MLX when changing shared code.

The product name is **Klam**; the Python package is still `vox_darija` and
settings still use the `VOX_` prefix. Renaming those is a pending mechanical
change — do not half-apply it, because imports, the Makefile, `pyproject.toml`,
the deploy trees and the tests all have to move together.

## Layout

- `backend/` — Python 3.12 + FastAPI. Package `vox_darija` under `src/`.
- `frontend/` — React + TS + Vite + Tailwind + Zustand.
- `deploy/modal/` — serverless GPU ASR endpoint (remote `voxtral` provider).
- `deploy/hf/` — assembles a Hugging Face Space.
- `design/` — brand assets.
- `docs/PLAN.md` — architecture, schema, mlx-audio findings, milestones, risks.

## Commands

Run from the repo root unless noted.

```bash
make setup            # uv venv + install core/dev deps (into backend/.venv)
make setup-mlx        # + install MLX provider deps (macOS only)
make setup-frontend   # pnpm install (frontend)
make model            # build the 8-bit MLX speech model (~20 GB disk)
make fonts            # (re)fetch bundled OFL fonts
make doctor           # check ffmpeg/libass/fonts
make test             # pytest (backend) + vitest (frontend)
make lint             # ruff (backend) + oxlint (frontend)
make fmt              # ruff format
make dev              # backend on :8001 (in-process MLX)
make frontend         # Vite dev server on :5173
make dev-mac          # mlx-audio server + backend (HTTP mode)
make dev-all          # backend (mock ASR) + frontend
make frontend-build   # production frontend bundle
cd frontend && pnpm test   # vitest (frontend)
cd frontend && pnpm lint   # oxlint (frontend)
```

The venv lives at `backend/.venv`. Always pass
`--python backend/.venv/bin/python` to `uv pip`, since a stray `VIRTUAL_ENV` in
the shell otherwise sends the install elsewhere.

## The speech model

`make model` converts `mistralai/Voxtral-Mini-4B-Realtime-Arabic` into an 8-bit
MLX model at `~/models/voxtral-ar-8bit`. Two things to know before touching this:

- **The Hub repo cannot be loaded directly.** It ships weights twice (Mistral's
  `consolidated.safetensors` and an HF-format `model.safetensors`) under
  different key schemes; mlx-audio's generic loader merges both and the result is
  garbage after `sanitize()`. It is a conversion source, not a model.
- **mlx-audio 0.4.5 copies `consolidated.safetensors` into the output**, which
  the `model` target deletes afterwards. Without that, the stray file is
  re-downloaded and merged on the next load.

`model_ref.resolve_mlx_model` accepts either a local directory or a Hub repo id
and mirrors mlx-audio's own path heuristic.

## Conventions

- **Python**: typed (`from __future__ import annotations`), ruff (`E F I W UP B`),
  no comments unless necessary, stdlib-first, no heavy deps without cause.
- **Schema first**: `backend/src/vox_darija/schema.py` (Pydantic) is the single
  source of truth; the frontend mirrors it with Zod (`frontend/src/schema.ts`).
  Validate on save/load.
- **ASR**: `ASRProvider.transcribe(audio, sample_rate, language) -> str`; the
  `Pipeline` owns all timing (VAD → chunks → segmentation → alignment).
- **RTL/Arabic**: never assume LTR; use `direction` from the schema, test mixed
  Arabic/Latin/numeral text, and verify shaping in both preview and export.
- **Export**: ASS is generated from the same schema (`export/ass.py`); lengths
  are px at `reference_height` (1080) and scaled by `height/1080` so the preview
  and libass export match. Burn-in needs an FFmpeg with libass (`ffmpeg-full`,
  auto-detected; `make doctor`). Same fonts are served to the browser and passed
  to libass via `fontsdir`.
- **Jobs**: in-process asyncio queue + SQLite store; progress over SSE. No Redis.
- **Frontend**: TS with `verbatimModuleSyntax`/`erasableSyntaxOnly` (no `enum`;
  use string unions / Zod). `import type` for type-only imports. State in
  `frontend/src/store.ts` (Zustand); undo/redo via a snapshot history.
- **No telemetry, no mandatory cloud services.** Everything runs offline.

## Tests

- Unit: segmentation, VAD, chunking, SRT/VTT, schema round-trip, direction.
- Arabic: `tests/test_shaping.py` (HarfBuzz via `uharfbuzz`) asserts joined
  forms / no missing glyphs; `frontend/tests/golden.test.ts` (Skia via
  `@napi-rs/canvas`) compares Arabic + mixed-text renders to committed goldens
  (regenerate with `UPDATE_GOLDEN=1 pnpm test`).
- Integration: `tests/test_pipeline.py` (full pipeline with a mock ASR),
  `tests/test_api.py` (upload → job → result via TestClient, mock ASR).
- Real-model tests are manual only (need the Voxtral model + MLX on macOS).

Fonts (OFL-1.1) are committed under `frontend/public/fonts/`; refresh with
`make fonts`. The preview and (M4) export must use these same fonts.
