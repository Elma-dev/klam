# PLAN — Vox Darija (open-source auto-captioning video editor, Arabic-first)

## 1. Goal

Web app: upload a video → auto-transcribe to timed captions (Voxtral, served via
mlx-audio on macOS) → edit text/timings → fully style captions in a live preview
→ export burned-in MP4 / SRT / VTT / ASS. Arabic + RTL is first-class; also
French, English, and Darija↔French code-switching. Fully local and offline.

## 2. Environment (verified 2026-10-10)

| Item | Value |
|---|---|
| Hardware | Apple M4 (arm64), macOS 26.2 |
| Python | 3.12.11, `uv` 0.11.8 |
| Node | v24.3.0, pnpm 10.22.0 |
| FFmpeg | 9.0.2 (Homebrew) — **no `--enable-libass`** (see Risks) |
| mlx-audio | 0.4.5 (MIT), mlx 0.32.0, mlx-qwen3-asr 0.3.2, faster-whisper 1.2.1 |
| Docker | 28.5.1 + Compose v2.40.3 |
| Models | `~/models/voxtral-ar-{4bit,8bit,bf16}` (Mistral `VoxtralRealtimeForConditionalGeneration`, Arabic, 16 kHz, streaming) |

## 3. mlx-audio findings (from source of v0.4.5)

1. **Endpoints** (`mlx_audio/server.py`):
   - `POST /v1/audio/transcriptions` — multipart `file`, `model`, `language`,
     `word_timestamps`, `timestamp_granularities`, `response_format`
     (`text`/`json`/`verbose_json`/`ndjson`), `max_tokens` (1024),
     `chunk_duration` (**30.0 s**), `stream`, `context`, `prefill_step_size`.
   - `POST /v1/audio/speech`, `GET/POST/DELETE /v1/models`,
     `WS /v1/audio/transcriptions/realtime`, `WS /v1/realtime` (OpenAI Realtime).
2. **Chunking**: server default `chunk_duration=30.0 s`. We chunk at ~30 s,
   silence-aligned, with offset-correct merging.
3. **Timestamps**: the Voxtral *realtime* model's `generate()` returns
   `STTOutput(text=...)` only; `stream=True` yields text deltas only — **no
   segment or word timestamps, no language field**. ⇒ forced alignment required.
4. **Language**: `generate(audio, *, max_tokens, temperature, verbose, stream,
   transcription_delay_ms, **kwargs)` — no functional `language` param; the
   model is Arabic-only. Darija↔French code-switching is handled by Voxtral.
   Pure fr/en will need a future `WhisperProvider` (interface is ready).
5. **Two in-process modes**: `mlx_audio.stt.load()` → `model.generate()` (batch)
   or `model.create_streaming_session()` (stateful `feed()`/`step()`); plus HTTP
   mode against the server.
6. **Forced alignment already available**: `stt/models/qwen3_forced_aligner`
   (CTC) and `lasr_ctc`; `mlx-qwen3-asr` also ships `forced_aligner.py`.

## 4. Architecture

```
frontend/  React + TS + Vite + Tailwind + Zustand   (M2)
backend/   Python + FastAPI                         (M1)
  src/vox_darija/
    schema.py        shared caption+style JSON schema (Pydantic)
    asr/             ASRProvider protocol + providers
    audio/           ffmpeg extraction, VAD, chunking
    alignment.py     replaced by aligners.py + wordmap.py (word timestamps)
    segmentation.py  caption segmentation rules
    export/          SRT / VTT / ASS writers (ASS in M4)
    jobs.py          in-process asyncio queue + SQLite store
    config.py        env-driven settings
    main.py          FastAPI app (upload, jobs, SSE)
scripts/  Makefile  docker-compose.yml
```

- **Job queue**: in-process asyncio workers + SQLite job/task table; progress
  over SSE. No Redis (offline, no mandatory services).
- **ASR**: `MLXAudioProvider` (default, two modes: HTTP + in-process),
  `VoxtralProvider` (Linux/NVIDIA: Transformers or vLLM/OpenAI-compatible),
  `WhisperProvider` (future, pure fr/en).

## 5. Data schema (single source of truth)

`Project = {version, media, language, segments[], style, presets[]}`,
`Segment = {id, start, end, text, words[]?, speaker?, dir?}`,
`Word = {word, start, end}`. Defined in `backend/src/vox_darija/schema.py`
(Pydantic) and mirrored in the frontend with Zod. Validated on save/load.

## 6. Milestones

- **M1** — schema + backend pipeline (upload, extraction, VAD, MLXAudioProvider,
  SRT output) + CLI + tests. *(done)*
- **M2** — frontend player + transcript editor + live captions. *(done)*
- **M3** — styling panel + presets + RTL/Arabic correctness + golden tests.
  *(done: bundled OFL fonts, full style panel, per-segment direction, entrance
  animations, built-in + user presets; HarfBuzz shaping tests (uharfbuzz) and
  Skia golden-image tests (@napi-rs/canvas).)*
- **M4** — ASS generation + burned-in export matching the preview. *(done:
  ASS generator from the shared style model, libass burn-in with bundled fonts,
  SRT/VTT/ASS/JSON export, aspect presets (source/16:9/1:1/9:16), asset serving
  with HTTP range, export jobs + download endpoint, pixel-verified export test.)*
- **M5** — word-level highlight animations, Linux/Docker setup, polish, CI.

## 7. Risks

1. **FFmpeg has no libass** — burned-in export (M4) requires `brew install
   libass` + FFmpeg rebuild. Health check fails clearly until then.
2. **Arabic-only model** vs pure fr/en requirement — needs `WhisperProvider`
   (deferred, interface already extensible).
3. **Preview ↔ export parity** for Arabic shaping/bidi — mitigated by using the
   same fonts + HarfBuzz/libass + golden-image tests.
4. **Shared venv** — building into a machine-wide or shared virtualenv risks
   breaking unrelated work; we use a dedicated project venv via `uv`.

## 8. Empirically confirmed (M1, real model on a 24 s Darija test clip)

- In-process `MLXAudioProvider` works end-to-end: a 24 s Darija clip transcribed
  to correct Arabic text, including code-switching ("code switching بين الدارجة
  والفرنسية والإنجليزية"). Total wall time ~26 s including model load.
- Confirmed: `generate()` returns text only (no timestamps, no language), so
  caption timing is proportional until CTC alignment lands.
- A single 24 s chunk transcribes fine; the server's 30 s `chunk_duration`
  default is a safe ceiling assumption (still to be stress-tested at 60 min).

## 9. Open questions

- Exact per-request audio length ceiling at 60+ min (stress test in a later
  milestone; 30 s chunks confirmed working).
- Code-switching accuracy targets (Darija with French words) — `audio1.wav`
  is a good reference; add a golden transcript for regression testing.

## 10. Export & preview parity (M4)

- **libass**: Homebrew's `ffmpeg` formula no longer ships libass; we use
  `ffmpeg-full` (keg-only) and auto-detect a libass-capable build
  (`backend/src/vox_darija/ffmpeg.py`). `/health` and `make doctor` report it.
- **Shared geometry**: `CaptionStyle` lengths are px at `reference_height`
  (1080). The preview scales by `displayedHeight/1080`; the ASS export scales by
  `outputHeight/1080` with `PlayResX/Y = output size`. So font size, margins,
  outline, padding, and shadow match proportionally.
- **Fonts**: the same bundled OFL fonts are served to the browser (`/fonts`) and
  passed to libass via the `ass` filter's `fontsdir`. HarfBuzz + FriBidi do the
  shaping/bidi in both.
- **Direction**: each segment stores a detected direction; ASS lines get an
  RLM/LRM mark so libass resolves the paragraph direction as intended.
- **Known differences** (documented, not bugs):
  - ASS has no shadow *blur*; we approximate with a single shadow distance.
  - A background box (`BorderStyle=3`) and a text outline are mutually exclusive
    in one ASS style; the box wins when `background.opacity > 0`.
  - Variable-font weights are approximated: libass picks the nearest instance.
  - Gradual karaoke word-by-word animation in export is M5 (the preview shows it).

## 11. Word-level timing / sync (fixes voice–text drift)

Voxtral returns text only, so the pipeline aligns each chunk's transcript to the
audio to get word-level timestamps. The first attempt used a Qwen3 forced
aligner, but its `support_languages` has no Arabic — on Darija it collapsed whole
runs of words to zero duration and stretched the last word into silence, showing
up as drift, phantom gaps, and overlapping segments.

Now `aligners.WhisperAligner` decodes each chunk with mlx-audio Whisper
(`mlx-community/whisper-large-v3-turbo-asr-fp16`; multilingual, Arabic included)
using `word_timestamps=True` (cross-attention DTW). Whisper's transcript can
differ from Voxtral's, so `wordmap.align_transcript` matches the two word
sequences (orthography folded) and transfers timings: matched words inherit
Whisper's boundaries, runs the two disagree on are filled proportionally between
the surrounding anchors, then everything is forced monotonic with a minimum
duration.

- `segmentation.segment_words()` builds captions from those word times, breaking
  on sentence-enders, long pauses, max duration, and the line budget, so captions
  follow the voice and real pauses are kept.
- The pipeline clamps each word to its chunk's speech bounds, so a bad boundary
  can't overlap the next chunk or extend into silence.
- `MLXAudioProvider` stays a pure text source; the aligner is provider-agnostic
  (`WhisperAligner.align(audio, sr, text, language)`).
- `VOX_TIMED_ALIGNMENT` (default on, needs mlx) falls back to proportional timing
  when the aligner is unavailable (mock / HTTP / CI).
- Tuning: `VOX_ALIGNER_MODEL`, `VOX_ALIGNER_LANGUAGE` (ISO code; empty = follow
  the project language).

An earlier attempt derived timing from the realtime streaming session's frame
rate; it worked but had ~0.4 s quantisation artefacts that fragmented captions.

