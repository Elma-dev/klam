"""The remote-endpoint provider, exercised against a fake HTTP transport.

No network, no GPU, no Modal account — `httpx.MockTransport` stands in for the
served model and lets us assert exactly what goes over the wire.
"""

from __future__ import annotations

import httpx
import numpy as np
import pytest

from vox_darija.asr.voxtral import VoxtralProvider, parse_words
from vox_darija.config import Settings

AUDIO = np.zeros(1600, dtype=np.float32)


def _settings(**overrides) -> Settings:
    base = {
        "voxtral_base_url": "https://asr.test",
        "voxtral_api_key": "tok",
        "voxtral_timeout": 5.0,
        "timed_alignment": True,
    }
    base.update(overrides)
    return Settings(**base)


def _provider(handler, **overrides) -> VoxtralProvider:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return VoxtralProvider(_settings(**overrides), client=client)


def test_sends_auth_header_and_a_real_wav() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("Authorization")
        seen["path"] = request.url.path
        seen["body"] = request.read()
        return httpx.Response(200, json={"text": "شكرا"})

    _provider(handler).transcribe_result(AUDIO, 16000, "ar")

    assert seen["auth"] == "Bearer tok"
    assert seen["path"] == "/v1/audio/transcriptions"
    body = seen["body"]
    assert isinstance(body, bytes)
    # A RIFF header, not bare samples behind a .wav filename.
    assert b"RIFF" in body
    assert b"WAVE" in body


def test_word_timestamps_only_requested_when_alignment_is_on() -> None:
    sent: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent["body"] = request.read().decode("utf-8", "replace")
        return httpx.Response(200, json={"text": "x"})

    _provider(handler).transcribe_result(AUDIO, 16000, "ar")
    assert "verbose_json" in sent["body"]
    assert "word_timestamps" in sent["body"]

    _provider(handler, timed_alignment=False).transcribe_result(AUDIO, 16000, "ar")
    assert "verbose_json" not in sent["body"]
    assert "word_timestamps" not in sent["body"]


def test_parses_words_into_schema_words() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "text": "شكرا لكم",
                "words": [
                    {"word": "شكرا", "start": 0.0, "end": 0.4},
                    {"word": "لكم", "start": 0.4, "end": 0.9},
                ],
            },
        )

    result = _provider(handler).transcribe_result(AUDIO, 16000, "ar")

    assert result.text == "شكرا لكم"
    assert result.ref_words is not None
    assert [(w.word, w.start, w.end) for w in result.ref_words] == [
        ("شكرا", 0.0, 0.4),
        ("لكم", 0.4, 0.9),
    ]


def test_absent_words_are_none_not_empty() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"text": "شكرا"})

    assert _provider(handler).transcribe_result(AUDIO, 16000, "ar").ref_words is None


def test_transcribe_still_returns_plain_text() -> None:
    """The required protocol surface must keep working."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"text": "  شكرا  "})

    assert _provider(handler).transcribe(AUDIO, 16000, "ar") == "شكرا"


def test_http_error_is_raised() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    with pytest.raises(httpx.HTTPStatusError):
        _provider(handler).transcribe_result(AUDIO, 16000, "ar")


def test_no_endpoint_configured_is_an_error() -> None:
    provider = VoxtralProvider(
        Settings(voxtral_base_url="", voxtral_model_id="", asr_provider="voxtral")
    )
    with pytest.raises(RuntimeError):
        provider.transcribe(AUDIO, 16000, "ar")


def test_parse_words_skips_malformed_entries() -> None:
    assert parse_words(None) is None
    assert parse_words([]) is None
    assert parse_words([{"word": "", "start": 0.0, "end": 1.0}]) is None
    assert parse_words([{"word": "a", "start": 1.0, "end": 1.0}]) is None  # zero length
    assert parse_words([{"nope": 1}]) is None
    assert parse_words([{"word": "a", "start": "x", "end": "y"}]) is None

    kept = parse_words(
        [{"word": "ok", "start": 0.0, "end": 0.5}, {"word": "bad", "start": 0.5}]
    )
    assert kept is not None and [w.word for w in kept] == ["ok"]


def test_retries_a_dropped_cold_start_request(monkeypatch) -> None:
    """A scaled-to-zero endpoint loses the request that wakes it; one retry saves the job."""
    monkeypatch.setattr("vox_darija.asr.voxtral.time.sleep", lambda _s: None)
    seen: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(1)
        if len(seen) < 2:
            return httpx.Response(500, text="modal-http: invalid function call")
        return httpx.Response(
            200, json={"text": "شكرا", "words": [{"word": "شكرا", "start": 0.0, "end": 0.4}]}
        )

    result = _provider(handler).transcribe_result(AUDIO, 16000, "ar")

    assert len(seen) == 2, "should have retried exactly once"
    assert result.text == "شكرا"
    assert result.ref_words is not None


def test_gives_up_after_the_attempt_limit(monkeypatch) -> None:
    monkeypatch.setattr("vox_darija.asr.voxtral.time.sleep", lambda _s: None)
    seen: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(1)
        return httpx.Response(503, text="unavailable")

    with pytest.raises(httpx.HTTPStatusError):
        _provider(handler).transcribe_result(AUDIO, 16000, "ar")
    assert len(seen) == 3  # _MAX_ATTEMPTS


def test_does_not_retry_client_errors() -> None:
    seen: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(1)
        return httpx.Response(401, text="nope")

    with pytest.raises(httpx.HTTPStatusError):
        _provider(handler).transcribe_result(AUDIO, 16000, "ar")
    assert len(seen) == 1, "a 401 is not a transient failure"
