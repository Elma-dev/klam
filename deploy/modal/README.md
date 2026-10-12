# Modal ASR endpoint

A serverless GPU transcription endpoint for Klam.

The app's models are Apple-MLX-only (`mlx-audio` Voxtral, plus an `mlx-audio`
Whisper aligner), which pins the whole product to a Mac. This service moves the
two GPU-bound stages off-box behind an HTTP endpoint, so the app — VAD, chunking,
caption segmentation, the ffmpeg/libass export — runs anywhere.

```
app (anywhere)  ──POST wav──▶  Modal GPU  ──▶  Voxtral (Arabic)  → text
                                            └─▶ Whisper           → word timings
```

## Why two models

Voxtral is the accurate Darija transcriber but returns **no timings**, and the
caption modes that follow the voice (karaoke, one word at a time) depend on word
timings. Whisper supplies them. Because the app maps the aligner's words onto
Voxtral's text with `wordmap.align_transcript`, a mediocre Whisper transcript
cannot corrupt captions — it can only make the timings more proportional.

The aligner runs on **transformers Whisper**, not faster-whisper: CTranslate2
links against CUDA 12 (`libcublas.so.12`) while current torch wheels bundle
CUDA 13, and the two cannot be loaded into the same process. Staying on torch
keeps the container to a single CUDA stack.

## The contract

`POST /v1/audio/transcriptions`, multipart, `Authorization: Bearer <token>`.

| field | notes |
|---|---|
| `file` | WAV bytes (16 kHz mono; other rates are resampled) |
| `language` | `ar` / `fr` / `en`, or empty/`auto` to let the aligner detect |
| `response_format` | `json` (default) or `verbose_json` |
| `word_timestamps` | `true` also selects the verbose shape |

`json` → `{"text": "..."}` — **skips the aligner**, roughly halving GPU time.

`verbose_json` →

```json
{
  "text": "شكرا لكم على المشاهدة",
  "language": "ar",
  "duration": 30.0,
  "model": "mistralai/Voxtral-Mini-4B-Realtime-Arabic",
  "words": [{"word": "شكرا", "start": 0.12, "end": 0.44}],
  "words_source": "aligner:transformers/openai/whisper-large-v3"
}
```

**`words` are not timings of `text`.** They come from the aligner model and are
mapped onto `text` by the app. `words_source` states this on the wire so the
field is never mistaken for OpenAI's `words` (which *is* timings of `text`).

`GET /healthz` → `{"status": "ok", "model": "..."}`.

## Deploy

```bash
pip install modal && modal setup

# one shared secret; use a long random string
modal secret create klam-asr KLAM_ASR_TOKEN=$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')

make modal-weights    # one-time: cache ~11 GB of weights on the Volume
make modal-deploy     # prints a stable https://<workspace>--klam-asr-web.modal.run
```

`make modal-serve` runs a hot-reloading dev endpoint instead.

Do not skip `modal-weights`: without it the first request pays the Hub download
and will likely exceed the request timeout.

## Point the app at it

```bash
export KLAM_ASR_PROVIDER=voxtral
export KLAM_VOXTRAL_BASE_URL=https://<workspace>--klam-asr-web.modal.run
export KLAM_VOXTRAL_API_KEY=<the same KLAM_ASR_TOKEN>
```

Then run the backend as usual. The app sends one request per VAD chunk (~30 s),
so a 52 s clip is two calls.

## Smoke test

```bash
curl -s "$KLAM_VOXTRAL_BASE_URL/healthz"

curl -s "$KLAM_VOXTRAL_BASE_URL/v1/audio/transcriptions" \
  -H "Authorization: Bearer $KLAM_VOXTRAL_API_KEY" \
  -F file=@clip.wav \
  -F language=ar \
  -F response_format=verbose_json | python3 -m json.tool
```

First call is cold (weights load into VRAM); run it twice to see warm latency.

## Measured behaviour

From a live deployment on an L40S, one 30 s chunk:

| | duration | of which execution |
|---|---|---|
| warm | **16.2 s** | 15.9 s |
| first request after scaling to zero | **~60–90 s** | 17.4 s |

So the number to plan around: **warm ≈ 16 s per 30 s chunk**, and a 52 s clip is
two chunks ≈ 32 s of GPU. Most of the cold-start time is the container reading
~15 GB of weights from the Volume, not inference.

**The first request against a scaled-to-zero endpoint may be dropped** with
`modal-http: internal error: status InternalFailure: Server has lost track of
input` — the container is still booting and Modal loses the input. This is
platform behaviour, not a fault in the service. `VoxtralProvider` retries
transient failures (`asr/voxtral.py`), which is what makes an end-to-end cold
run succeed; a caller hitting the endpoint directly must retry once too.
Raising `memory` did **not** change this — it is not an out-of-memory kill.

### Memory snapshots did not help

`enable_memory_snapshot=True` with `experimental_options={"enable_gpu_snapshot":
True}` is enabled here, and Modal does log `Creating GPU memory snapshot for
Function`. But no restore was ever observed, and the cold start stayed at ~72 s
of waiting. That is consistent with the documented caveat that snapshots do not
speed up weight loading from storage — which is what dominates this container.
Treat them as unproven here; the client retry is what actually covers cold
starts. Consider removing the flags if they add snapshot-creation cost on every
deploy without a measurable win.

## Cost and warmth

`scaledown_window=900` keeps the GPU for fifteen minutes after the last request,
covering an editing session for roughly **$0.49** of idle time. `min_containers=0`
means an idle endpoint costs nothing; raising it to 1 removes the cold start
entirely but bills continuously (~$1,400/month on an L40S) — not worth it for
single-user use.

`gpu=["L40S", "A100-40GB"]` is tried in order. Both models together need roughly
16–20 GB, so an L40S (48 GB) is comfortable.

## What the first real run established

Recorded from the first end-to-end request against a live deployment:

- **Offline `generate()` works.** The transformers docs describe batch
  transcription for this streaming-architected model, and it holds: Voxtral
  produced a transcript on a real 30 s chunk. (The request then failed further
  down, at the aligner — which is itself proof Voxtral had already succeeded.)
- **The `AutoProcessor` call signature is as documented** — no change needed to
  `inference.py:_voxtral_text`.
- **faster-whisper could not be used at all.** CTranslate2 needs
  `libcublas.so.12`; the torch wheels here ship CUDA 13, so the process died
  with `Library libcublas.so.12 is not found or cannot be loaded`. That is why
  the aligner now runs on transformers Whisper. Do not reintroduce CTranslate2
  without pinning a matching CUDA stack.

Still worth checking on your own clips:

- **Fine-tune parity.** Modal runs the public Arabic checkpoint. The local
  `~/models/voxtral-ar-*` directories are MLX-quantised and cannot be loaded by
  CUDA transformers, so transcripts will differ slightly from the Mac path.
- **Cold-start time**, dominated by reading the weights from the Volume.

## Tests

The routing, auth and response envelope are testable on a CPU machine — no GPU,
no torch, no Modal account:

```bash
python -m pytest deploy/modal        # from the repo root
```

`service.py` and `contract.py` deliberately import nothing heavier than FastAPI,
and the models sit behind the `Engine` protocol that `test_service.py` fakes.
