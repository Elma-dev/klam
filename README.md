<img src="design/klam/klam-icon.svg" alt="Klam" width="96">

# Klam

An auto-captioning video editor for Arabic and Darija. Upload a clip, edit the
captions, style them against a live preview, export a burned-in video.

It runs on your own machine. Apple Silicon uses MLX; an NVIDIA GPU uses PyTorch.

![Editing Arabic captions in Klam](docs/demo.gif)

## Features

- Speech to timed captions
- Editable transcript: split, merge, delete, retime, undo/redo
- Styling: bundled Arabic fonts, colour, outline, shadow, background, position,
  RTL/LTR, per-word highlight
- Export: burned-in MP4 (libass), SRT, VTT, ASS, project JSON

Arabic is handled throughout: RTL layout, letter joining, mixed
Arabic/Latin/numeral text, and Darija and French code-switching. The preview and
the exported file come from the same caption schema and the same font files.

## Requirements

Common to every platform:

- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- Node and pnpm
- FFmpeg, required for every job since audio is extracted from the video
- FFmpeg built with libass, needed only for burned-in MP4 export

Then pick a transcription backend, set with `KLAM_ASR_PROVIDER` in
`backend/.env` (copy `.env.example`) or the environment:

| Provider | Runs on | Notes |
|---|---|---|
| `mlx` (default) | macOS, Apple Silicon | Fastest on a Mac. Needs a conversion step. |
| `local-gpu` | Linux or Windows, NVIDIA GPU | PyTorch, in-process. Downloads its models on first run. Wants 16 to 20 GB of VRAM. |
| `voxtral` | Anything, including a CPU-only box | A remote endpoint, see [`deploy/modal/`](deploy/modal/). Sends your audio off the machine. |
| `mock` | Anything | Fixed text and no model, for working on the editor. |

## Install

### macOS, Apple Silicon

```bash
git clone https://github.com/Elma-dev/klam.git
cd klam
make setup
make setup-mlx
make model
make setup-frontend
```

### Linux or Windows, NVIDIA GPU

```bash
git clone https://github.com/Elma-dev/klam.git
cd klam
make setup
make setup-frontend
cd backend
uv pip install --python .venv/bin/python -e ".[local-gpu]"
cp ../.env.example .env      # set KLAM_ASR_PROVIDER=local-gpu
```

The first transcription downloads the models from the Hub.

### Run

```bash
make dev          # backend on http://localhost:8001
make frontend     # UI on http://localhost:5173
```

Open <http://localhost:5173>.

### Without a model

```bash
make dev-all
```

Runs the backend with a mock transcriber that returns fixed Arabic text, so you
can work on the editor and export without downloading anything. FFmpeg is still
required.

## The speech model

`make model` converts `mistralai/Voxtral-Mini-4B-Realtime-Arabic` into an 8-bit
MLX model at `~/models/voxtral-ar-8bit`. Budget about 20 GB of free disk (the
source repository ships ~18 GB of weights, the result is ~4.7 GB) and about 9 to
10 GB of RAM at peak.

The Mistral repository cannot be loaded directly. It ships its weights twice, in
Mistral's `consolidated.safetensors` layout and in HuggingFace format, under
different key schemes. mlx-audio's loader globs every `.safetensors` file and
merges them, which produces garbage after the model's `sanitize()` step. It is a
conversion source, not a model.

`KLAM_MLX_MODEL` accepts either a local directory or a Hub repo id, and a repo id
is downloaded on first use:

```bash
export KLAM_MLX_MODEL=some-user/voxtral-ar-8bit-mlx
```

## CLI

```bash
cd backend
.venv/bin/python -m klam transcribe clip.mp4 --lang ar --format srt
.venv/bin/python -m klam transcribe clip.mp4 --provider mock --format vtt
```

`--provider` is one of `mlx`, `voxtral`, `local-gpu`, `mock`. `--format` is one
of `srt`, `vtt`, `json`. Without `--output` it writes to stdout.

## Development

```bash
make test     # pytest + vitest
make lint     # ruff + oxlint
make fmt      # ruff format
make doctor   # ffmpeg, libass, fonts
make fonts    # (re)fetch the bundled OFL fonts
```

Arabic rendering is tested rather than assumed: HarfBuzz shaping assertions in
the backend, and Skia golden-image comparisons in the frontend.

## Architecture

```
frontend/   React, TypeScript, Vite, Tailwind, Zustand
  src/schema.ts        Zod mirror of the backend schema
  src/store.ts         segments, style, undo/redo, upload
  src/i18n.ts          Arabic and English UI strings
  src/direction.ts     bidi first-strong detection
  src/fonts.ts         bundled-font loader
  src/lib/             canvas rendering, snapping, platform presets
  src/components/      player, overlay, transcript, timeline, panels
  public/fonts/        bundled OFL fonts and their licence texts

backend/    Python 3.12, FastAPI
  src/klam/
    schema.py          caption and style schema
    pipeline.py        media -> audio -> VAD -> chunks -> ASR -> captions
    asr/               providers: mlx, voxtral, local-gpu, mock
    aligners.py        Whisper word timings
    wordmap.py         maps reference words onto the transcript
    model_ref.py       local directory or Hub repo id
    audio/             extraction, VAD, chunking
    segmentation.py    line breaking
    direction.py       bidi first-strong detection
    export/            ASS, SRT/VTT, libass burn-in
    ffmpeg.py          libass-capable FFmpeg detection
    jobs.py            asyncio queue and SQLite store
    main.py            FastAPI app
```

Voxtral returns text without word timestamps. Whisper decodes the same audio with
word timestamps, and Klam maps those onto the Voxtral transcript by sequence
alignment. A Whisper transcript that differs from Voxtral's cannot corrupt the
captions, only the timings. With no aligner available, timings fall back to a
proportional spread.

## Credits

- Speech recognition: Mistral AI's
  [`Voxtral-Mini-4B-Realtime-Arabic`](https://huggingface.co/mistralai/Voxtral-Mini-4B-Realtime-Arabic).
  Its model card lists Modern Standard Arabic plus Moroccan, Algerian, Tunisian,
  Libyan, Hassaniya, Gulf, Egyptian, Sudanese, Iraqi, Levantine and Chadian
  Arabic. Check that card for licence terms before redistributing a converted
  copy.
- Word timings: OpenAI's Whisper, `openai/whisper-large-v3-turbo`.
- Apple Silicon inference: [mlx-audio](https://github.com/Blaizzy/mlx-audio).
- Fonts: Cairo, Tajawal, Noto Naskh Arabic, Amiri, IBM Plex Sans Arabic, Inter.
  All SIL OFL 1.1, with licence texts committed alongside them.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

Apache-2.0. See [LICENSE](LICENSE).
