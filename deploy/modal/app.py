"""Modal app: a serverless GPU transcription endpoint for Vox Darija.

Deploy:

    modal secret create vox-darija-asr VOX_ASR_TOKEN=<a long random string>
    modal run deploy/modal/app.py::download_models   # one-time weight prefetch
    modal deploy deploy/modal/app.py

Then point the app at it:

    VOX_ASR_PROVIDER=voxtral
    VOX_VOXTRAL_BASE_URL=https://<workspace>--vox-darija-asr-web.modal.run
    VOX_VOXTRAL_API_KEY=<the same token>

The endpoint speaks the OpenAI transcription shape, so `VoxtralProvider` uses it
unchanged. See README.md for the smoke test.
"""

from __future__ import annotations

import os

import modal

APP_NAME = "vox-darija-asr"
HF_MOUNT = "/root/.cache/huggingface"
VOXTRAL_ID = os.environ.get(
    "VOXTRAL_MODEL_ID", "mistralai/Voxtral-Mini-4B-Realtime-Arabic"
)
ALIGNER_ID = os.environ.get("VOX_ALIGNER_MODEL_ID", "openai/whisper-large-v3-turbo")

# How long the GPU stays warm after the last request, in seconds.
#
# This is the dominant cost of scattered traffic: an idle warm container bills
# roughly $0.49 per 15 minutes, so a single visitor who then goes quiet costs
# about as much as several minutes of transcription. A launch is bursty, and a
# burst shares one warm container, which is the case this default suits.
#
# Lower it (60-120) if traffic arrives as a slow trickle rather than a spike —
# that cuts idle spend by ~90% at the price of more 60-90 s cold starts. Note
# that *raising* it never pays: staying warm around the clock would run to
# ~$47/day, more than a month of the free allowance.
#
# Override at deploy time: VOX_SCALEDOWN_WINDOW=120 make modal-deploy
SCALEDOWN_WINDOW = int(os.environ.get("VOX_SCALEDOWN_WINDOW", "900"))

app = modal.App(APP_NAME)

# Weights live on a Volume so they are fetched once, not on every cold start.
hf_cache = modal.Volume.from_name("vox-darija-hf", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg", "libsndfile1")
    .pip_install(
        "fastapi>=0.115",
        "python-multipart>=0.0.9",
        "numpy>=1.26",
        "soundfile",
        "torch>=2.8,<3",
        # VoxtralRealtimeForConditionalGeneration only exists from 5.2.0.
        "transformers>=5.2,<5.3",
        "huggingface_hub>=1.3,<2",
        "mistral-common[audio]>=1.9.0",
        # No faster-whisper/CTranslate2: it links against CUDA 12 while these
        # torch wheels bundle CUDA 13, and libcublas.so.12 is not present.
    )
    .env({"HF_HOME": HF_MOUNT})
    .add_local_python_source("contract", "service", "inference")
)


@app.function(image=image, volumes={HF_MOUNT: hf_cache}, timeout=3600)
def download_models() -> str:
    """Prefetch both models into the Volume.

    Run this once after deploying: without it the first request pays ~11 GB of
    Hub download and will likely hit the request timeout.
    """
    from huggingface_hub import snapshot_download

    for repo in (VOXTRAL_ID, ALIGNER_ID):
        snapshot_download(repo)
    hf_cache.commit()
    print(f"cached {VOXTRAL_ID} and {ALIGNER_ID}")
    return VOXTRAL_ID


@app.cls(
    image=image,
    gpu=["L40S", "A100-40GB"],
    # Loading ~15 GB of weights needs far more host RAM than the default allows.
    memory=32768,
    # Snapshot the container once the models are resident, so a later cold start
    # restores GPU state instead of re-reading ~15 GB from the Volume. GPU
    # snapshots are alpha and driver-dependent; without enable_gpu_snapshot the
    # GPU is unavailable inside a snap=True hook.
    enable_memory_snapshot=True,
    experimental_options={"enable_gpu_snapshot": True},
    volumes={HF_MOUNT: hf_cache},
    secrets=[modal.Secret.from_name(APP_NAME)],
    scaledown_window=SCALEDOWN_WINDOW,
    timeout=900,
    min_containers=0,  # never bill for an idle GPU
)
@modal.concurrent(max_inputs=1)
class ASRService:
    @modal.enter(snap=True)
    def load(self) -> None:
        """Load both models onto CUDA and warm them, then snapshot.

        `snap=True` means this work is captured: the weights are already in VRAM
        on restore, and the warmup keeps first-request latency out of the tail.
        """
        from inference import VoxtralEngine

        self.engine = VoxtralEngine(model_id=VOXTRAL_ID, aligner_id=ALIGNER_ID)
        self.engine.warmup()

    @modal.asgi_app()
    def web(self):
        from service import create_app

        return create_app(self.engine, os.environ.get("VOX_ASR_TOKEN"))
