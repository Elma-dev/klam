"""Environment-driven configuration."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KLAM_", env_file=".env", extra="ignore"
    )

    # Data / storage
    data_dir: Path = Path("data")

    # ASR
    asr_provider: str = "mlx"  # "mlx" | "local-gpu" | "voxtral" | "mock"
    language: str = "auto"  # auto | ar | fr | en

    # MLX provider
    mlx_mode: str = "inprocess"  # "inprocess" | "http"
    # A local directory, or a HuggingFace repo id to download on first run. The
    # default is exactly what `make model` produces.
    mlx_model: str = "~/models/voxtral-ar-8bit"
    mlx_base_url: str = "http://127.0.0.1:8000"
    mlx_timeout: float = 300.0

    # Voxtral provider (remote endpoint — Modal, vLLM, etc.)
    voxtral_model_id: str = ""
    voxtral_base_url: str = ""
    voxtral_api_key: str = ""  # bearer token, when the endpoint requires one
    # Generous by default: a serverless endpoint that has scaled to zero spends
    # most of a minute booting and loading weights before it can answer.
    voxtral_timeout: float = 300.0

    # Pipeline
    sample_rate: int = 16000
    chunk_duration: float = 30.0
    # Align the transcript to the audio for word-level timings (fixes voice/text
    # sync). Uses Whisper word timestamps (multilingual, Arabic included); falls
    # back to proportional when unavailable.
    timed_alignment: bool = True
    aligner_model: str = "mlx-community/whisper-large-v3-turbo-asr-fp16"
    aligner_language: str = ""  # ISO code override; empty = follow the project language

    # FFmpeg / export
    ffmpeg_bin: str = ""  # empty = auto-detect a libass-capable build
    ffprobe_bin: str = ""
    fonts_dir: str = ""  # empty = auto-detect frontend/public/fonts
    reference_height: int = 1080  # font_size units are px at this height

    # Caption segmentation
    max_chars_per_line: int = 42
    max_lines: int = 2
    max_duration: float = 7.0

    # Job concurrency. Keep this at 1 on a 2-vCPU host: concurrent ffmpeg
    # burn-ins contend for the same cores and finish slower than sequentially.
    max_workers: int = 2

    # VAD
    vad_frame_ms: int = 30
    vad_threshold: float = 0.02
    vad_min_speech: float = 0.25
    vad_min_silence: float = 0.4
    vad_padding: float = 0.15


def get_settings() -> Settings:
    return Settings()
