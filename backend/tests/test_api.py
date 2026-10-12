from __future__ import annotations

import os
import time
import wave

import numpy as np
import pytest


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    data_dir = tmp_path_factory.mktemp("data")
    os.environ["VOX_ASR_PROVIDER"] = "mock"
    os.environ["VOX_DATA_DIR"] = str(data_dir)
    os.environ["VOX_TIMED_ALIGNMENT"] = "false"

    from fastapi.testclient import TestClient

    from vox_darija.main import app

    with TestClient(app) as c:
        yield c


def _write_wav(path: str, audio: np.ndarray, sr: int = 16000) -> None:
    pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def _tone(freq: float, dur: float, sr: int = 16000, amp: float = 0.3) -> np.ndarray:
    t = np.arange(int(dur * sr)) / sr
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def test_upload_transcribe_job(client, tmp_path) -> None:
    sr = 16000
    audio = np.concatenate(
        [
            np.zeros(int(0.3 * sr), dtype=np.float32),
            _tone(440, 1.5),
            np.zeros(int(0.5 * sr), dtype=np.float32),
            _tone(880, 1.5),
            np.zeros(int(0.3 * sr), dtype=np.float32),
        ]
    )
    media = tmp_path / "sample.wav"
    _write_wav(str(media), audio)

    with open(media, "rb") as fh:
        resp = client.post(
            "/api/jobs",
            files={"file": ("sample.wav", fh, "audio/wav")},
            data={"language": "ar"},
        )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    for _ in range(50):
        status = client.get(f"/api/jobs/{job_id}").json()
        if status["status"] in ("done", "failed"):
            break
        time.sleep(0.1)

    assert status["status"] == "done", status
    assert status["result"]["segments"], "expected non-empty segments"
    assert "مرحبا" in status["result"]["segments"][0]["text"]


def test_health(client) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert "ffmpeg" in r.json()
