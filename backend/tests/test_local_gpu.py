"""The in-process GPU provider, checked without torch installed.

Constructing it needs torch, which this environment does not have — so these
tests pin the *shape* (the contract the pipeline depends on) rather than loading
a model. The model behaviour itself is exercised on the GPU hosts.
"""

from __future__ import annotations

import pytest


def test_module_imports_without_torch() -> None:
    """Importing it must not drag torch in.

    torch is absent from this environment, so the import succeeding *is* the
    assertion — a module-level torch import would raise here.
    """
    from vox_darija.asr import local_gpu

    assert local_gpu.LocalGPUProvider is not None


def test_satisfies_the_word_timed_contract() -> None:
    """The pipeline branches on this capability, so it must exist by shape."""
    from vox_darija.asr.local_gpu import LocalGPUProvider

    for method in ("transcribe", "transcribe_result", "warmup"):
        assert callable(getattr(LocalGPUProvider, method, None)), method
    assert LocalGPUProvider.name


def test_factory_selects_it_without_importing_torch() -> None:
    from vox_darija.asr.factory import get_provider
    from vox_darija.config import Settings

    with pytest.raises(ImportError):
        # No CUDA host here: it must fail loudly on the missing dependency
        # rather than silently falling back to another provider.
        get_provider(Settings(asr_provider="local-gpu"))
