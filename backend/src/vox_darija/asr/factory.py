"""Provider factory."""

from __future__ import annotations

from ..config import Settings
from .base import ASRProvider
from .mlx_audio import MLXAudioProvider
from .mock import MockProvider
from .voxtral import VoxtralProvider


def get_provider(settings: Settings) -> ASRProvider:
    if settings.asr_provider == "voxtral":
        return VoxtralProvider(settings)
    if settings.asr_provider == "mock":
        return MockProvider()
    if settings.asr_provider == "local-gpu":
        # Imported here so the rest of the package never needs torch (nor does
        # anyone who is not using this provider need it installed).
        try:
            from .local_gpu import LocalGPUProvider
        except ImportError as exc:  # pragma: no cover - depends on the install
            raise ImportError(
                "The 'local-gpu' provider needs torch and transformers. "
                "Install them with: uv pip install -e '.[local-gpu]'"
            ) from exc
        return LocalGPUProvider()
    if settings.asr_provider == "mlx":
        return MLXAudioProvider(settings)
    # Falling through to MLX on a typo would run a different model than the one
    # asked for, silently and at multi-gigabyte cost.
    known = "mlx, mock, voxtral, local-gpu"
    raise ValueError(f"Unknown VOX_ASR_PROVIDER {settings.asr_provider!r}. Use one of: {known}")
