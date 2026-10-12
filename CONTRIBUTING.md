# Contributing to Klam

Thanks for helping. This is an Arabic-first project, and the parts most likely to
break are the ones easiest to overlook: bidi text, font shaping, and word timing.
The notes below are mostly about those.

## Getting set up

Follow the [Quickstart](README.md#quickstart). For UI or pipeline work you can
skip the model entirely — `make dev-all` runs the backend with a mock transcriber
that returns fixed Arabic text, so you never download anything:

```bash
make setup && make setup-frontend
make dev-all      # backend on :8001, UI on :5173
```

## Before opening a pull request

```bash
make test     # backend pytest + frontend vitest
make lint     # ruff + oxlint
make fmt      # ruff format
```

CI runs the backend suite and lint. Both must pass.

## Conventions

**Python** — typed (`from __future__ import annotations` is in every module),
ruff clean under `E F I W UP B`, standard library first. Avoid new dependencies
unless they clearly earn their place; the project runs offline by design.

**Schema first.** `backend/src/klam/schema.py` (Pydantic) is the single
source of truth, and `frontend/src/schema.ts` (Zod) mirrors it. Change one and
you almost always owe the other a change. Anything that travels between the two
halves is validated on both sides.

**TypeScript** — `verbatimModuleSyntax` and `erasableSyntaxOnly` are on, so use
`import type` for type-only imports and string unions rather than `enum`.

**ASR providers** implement
`ASRProvider.transcribe(audio, sample_rate, language) -> str`. The `Pipeline`
owns every timing decision, so a provider should not try to.

## The Arabic and RTL rules

These are not style preferences — each one is a bug we have already hit:

- Never assume LTR. Take direction from the schema, and test text that mixes
  Arabic, Latin, and numerals in one line.
- Check shaping in **both** the preview and the export. They use the same fonts
  by design; if they diverge, that is the bug.
- Font sizes are pixels at `reference_height` (1080) and scale by `height/1080`.
  Keep it that way or the preview stops matching libass.
- A change that touches rendering should come with a test. Arabic is covered by
  HarfBuzz shaping tests in the backend and Skia golden-image tests in the
  frontend; regenerate the goldens only when the change is intended.

## Tests

- Unit: segmentation, VAD, chunking, SRT/VTT, schema round-trip, direction
- Arabic: `backend/tests/test_shaping.py`; frontend goldens via
  `UPDATE_GOLDEN=1 pnpm test`
- Integration: `backend/tests/test_pipeline.py` and `test_api.py`, both with a
  mock transcriber, so they need no model and no GPU

Real-model tests are manual: they need the Voxtral weights and MLX on macOS.

## Reporting bugs

Please include your platform (macOS version and chip), the exact command, and
what you expected. A short clip that reproduces a caption or timing problem is
worth more than a long description — Arabic timing bugs are usually far easier to
see than to read about.
