"""Mock provider for tests and offline smoke runs."""

from __future__ import annotations


class MockProvider:
    name = "mock"

    def __init__(self, transcript: str = "مرحبا بكم في الدارجة."):
        self.transcript = transcript
        self.calls = 0

    def transcribe(self, audio, sample_rate: int, language: str) -> str:
        self.calls += 1
        return self.transcript
