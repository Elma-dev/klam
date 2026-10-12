"""Route, auth and response-envelope tests — CPU only.

No torch, no modal, no GPU: the models sit behind the ``Engine`` protocol, and a
fake stands in. Run with ``pytest deploy/modal`` from the repo root.

The tests live next to the modules (rather than in a tests/ package) so pytest
puts this directory on ``sys.path`` and ``import service`` resolves the same way
it does inside the Modal container.
"""

from __future__ import annotations

import io
import wave
from dataclasses import dataclass, field

from contract import WordOut
from fastapi.testclient import TestClient
from service import create_app

TOKEN = "s3cret-token"


@dataclass
class FakeTranscript:
    text: str
    language: str | None = None
    duration: float = 0.0
    words: list[WordOut] = field(default_factory=list)
    words_source: str | None = None


class FakeEngine:
    model_id = "fake-model"

    def __init__(self) -> None:
        self.asked_for_words: list[bool] = []

    def transcribe(self, wav: bytes, language, with_words: bool) -> FakeTranscript:
        self.asked_for_words.append(with_words)
        assert wav[:4] == b"RIFF", "the service must forward a real WAV"
        return FakeTranscript(
            text="شكرا لكم",
            language=language,
            duration=1.0,
            words=[WordOut(word="شكرا", start=0.0, end=0.4)] if with_words else [],
            words_source="aligner:fake" if with_words else None,
        )


def _wav(samples: int = 800) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * samples)
    return buf.getvalue()


def _client(token: str | None = TOKEN) -> tuple[TestClient, FakeEngine]:
    engine = FakeEngine()
    return TestClient(create_app(engine, token)), engine


def _post(client: TestClient, auth: str | None = TOKEN, **form):
    headers = {"Authorization": f"Bearer {auth}"} if auth else {}
    data = {"response_format": "json"}
    data.update(form)
    return client.post(
        "/v1/audio/transcriptions",
        files={"file": ("audio.wav", _wav(), "audio/wav")},
        data=data,
        headers=headers,
    )


def test_healthz() -> None:
    client, _ = _client()
    body = client.get("/healthz").json()
    assert body["status"] == "ok"
    assert body["model"] == "fake-model"


def test_requires_a_token() -> None:
    client, engine = _client()
    assert _post(client, auth=None).status_code == 401
    assert _post(client, auth="wrong").status_code == 401
    assert engine.asked_for_words == []


def test_accepts_bearer_and_api_key() -> None:
    client, _ = _client()
    assert _post(client).status_code == 200

    resp = client.post(
        "/v1/audio/transcriptions",
        files={"file": ("audio.wav", _wav(), "audio/wav")},
        data={"response_format": "json"},
        headers={"X-API-Key": TOKEN},
    )
    assert resp.status_code == 200


def test_unauthenticated_when_no_token_is_configured() -> None:
    """Local `modal serve` convenience; a deployed Space always sets a token."""
    client, _ = _client(token=None)
    assert _post(client, auth=None).status_code == 200


def test_plain_json_returns_text_only_and_skips_the_aligner() -> None:
    client, engine = _client()
    resp = _post(client)
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"text": "شكرا لكم"}  # no words, no envelope padding
    assert engine.asked_for_words == [False]


def test_verbose_json_returns_words_and_names_their_source() -> None:
    client, engine = _client()
    resp = _post(client, response_format="verbose_json")
    assert resp.status_code == 200
    body = resp.json()
    assert body["text"] == "شكرا لكم"
    assert body["words"] == [{"word": "شكرا", "start": 0.0, "end": 0.4}]
    assert body["words_source"] == "aligner:fake"
    assert engine.asked_for_words == [True]


def test_word_timestamps_flag_alone_also_gets_words() -> None:
    client, engine = _client()
    resp = _post(client, word_timestamps="true")
    assert resp.status_code == 200
    assert resp.json()["words"]
    assert engine.asked_for_words == [True]


def test_language_auto_is_normalised_to_none() -> None:
    client, engine = _client()
    _post(client, language="auto", response_format="verbose_json")
    assert engine.asked_for_words == [True]


def test_empty_upload_is_rejected() -> None:
    client, _ = _client()
    resp = client.post(
        "/v1/audio/transcriptions",
        files={"file": ("audio.wav", b"", "audio/wav")},
        data={"response_format": "json"},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert resp.status_code == 400
