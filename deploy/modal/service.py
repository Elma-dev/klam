"""The HTTP surface: the transcription route, auth, and response shaping.

Deliberately imports nothing heavier than FastAPI and pydantic, so the routing,
the auth check and the response envelope are testable on a CPU machine with no
GPU, no torch and no Modal. The models live behind the ``Engine`` protocol in
``inference.py``.
"""

from __future__ import annotations

import logging
import secrets
from typing import Annotated, Protocol

from contract import TranscriptionResponse, WordOut
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import JSONResponse

log = logging.getLogger("vox-darija-asr")


class Transcript(Protocol):
    text: str
    language: str | None
    duration: float
    words: list[WordOut]
    words_source: str | None


class Engine(Protocol):
    model_id: str

    def transcribe(
        self, wav: bytes, language: str | None, with_words: bool
    ) -> Transcript:
        """Transcribe WAV bytes; include word timings when ``with_words``."""
        ...


def create_app(engine: Engine, token: str | None, public_model_name: str = "voxtral") -> FastAPI:
    app = FastAPI(title="Vox Darija ASR", version="1.0.0")

    if not token:
        log.warning("VOX_ASR_TOKEN is unset — the endpoint is UNAUTHENTICATED")

    @app.exception_handler(Exception)
    async def unhandled(_request: Request, exc: Exception) -> JSONResponse:
        """Surface the failure to the caller.

        This is an internal, token-guarded service; returning the exception text
        turns every failure into one request instead of a trip through the logs.
        """
        log.exception("transcription failed")
        return JSONResponse(
            status_code=500, content={"detail": f"{type(exc).__name__}: {exc}"}
        )

    def require_token(
        authorization: str | None = Header(default=None),
        x_api_key: str | None = Header(default=None),
    ) -> None:
        if not token:
            return  # local `modal serve` convenience; never true when deployed
        presented = ""
        if authorization and authorization.lower().startswith("bearer "):
            presented = authorization[7:].strip()
        elif x_api_key:
            presented = x_api_key.strip()
        if not presented or not secrets.compare_digest(presented, token):
            raise HTTPException(status_code=401, detail="invalid or missing token")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "model": engine.model_id}

    @app.post(
        "/v1/audio/transcriptions",
        response_model=TranscriptionResponse,
        response_model_exclude_none=True,
        dependencies=[Depends(require_token)],
    )
    def transcribe(
        file: Annotated[UploadFile, File()],
        model: Annotated[str, Form()] = "",
        language: Annotated[str, Form()] = "",
        response_format: Annotated[str, Form()] = "json",
        word_timestamps: Annotated[str, Form()] = "false",
    ) -> TranscriptionResponse:
        wav = file.file.read()
        if not wav:
            raise HTTPException(status_code=400, detail="empty file")

        # Only the verbose shape asks for the aligner pass — it roughly doubles
        # the GPU time per chunk, so a plain json request must not pay for it.
        verbose = response_format == "verbose_json" or word_timestamps.lower() in {
            "true",
            "1",
            "yes",
        }
        lang = language or None
        if lang == "auto":
            lang = None

        result = engine.transcribe(wav, lang, with_words=verbose)
        log.info(
            "transcribed %d bytes lang=%s verbose=%s words=%d",
            len(wav),
            result.language,
            verbose,
            len(result.words),
        )

        if not verbose:
            return TranscriptionResponse(text=result.text)

        return TranscriptionResponse(
            text=result.text,
            language=result.language,
            duration=result.duration,
            model=public_model_name,
            words=[WordOut(word=w.word, start=w.start, end=w.end) for w in result.words],
            words_source=result.words_source,
        )

    return app
