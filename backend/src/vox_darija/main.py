"""FastAPI application: upload, transcription jobs, export, progress (SSE)."""

from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    JSONResponse,
    PlainTextResponse,
    StreamingResponse,
)
from pydantic import BaseModel

from .asr.factory import get_provider
from .audio.extract import probe_media
from .config import get_settings
from .export import ExportOptions, burn_video, export_subtitles
from .ffmpeg import has_libass, resolve_ffmpeg
from .jobs import JobManager, JobStore
from .pipeline import transcribe_media
from .schema import Project

settings = get_settings()
store = JobStore(settings.data_dir / "jobs.sqlite3")
manager = JobManager(store, max_workers=settings.max_workers)
_provider = get_provider(settings)

UPLOADS = settings.data_dir / "uploads"
EXPORTS = settings.data_dir / "exports"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await manager.start()
    yield
    await manager.shutdown()


app = FastAPI(title="Vox Darija", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

_MEDIA_TYPES = {
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
    ".avi": "video/x-msvideo",
    ".3gp": "video/3gpp",
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".opus": "audio/opus",
}


def _reject_if_unreadable(media_path: Path) -> None:
    """Fail an unreadable upload here, with a clear message.

    Otherwise the first sign that a file is not really media is an FFmpeg error
    from the middle of the pipeline, which reads as a bug in the app.
    """
    try:
        probe_media(str(media_path), settings)
    except Exception as exc:  # noqa: BLE001
        media_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400, detail="That file could not be read as audio or video."
        ) from exc


class ExportRequest(BaseModel):
    asset_id: str
    project: dict
    format: str = "mp4"
    aspect: str = "source"
    mode: str = "fit"
    crf: int = 20
    preset: str = "medium"


class SubtitleRequest(BaseModel):
    project: dict
    format: str = "srt"


def _asset_path(asset_id: str) -> Path | None:
    matches = sorted(UPLOADS.glob(f"{asset_id}.*"))
    return matches[0] if matches else None


@app.get("/health")
async def health() -> JSONResponse:
    ffmpeg = resolve_ffmpeg(settings)
    return JSONResponse(
        {
            "ffmpeg": ffmpeg,
            "libass": has_libass(ffmpeg),
            "provider": settings.asr_provider,
        }
    )


@app.post("/api/jobs")
async def create_job(
    file: Annotated[UploadFile, File()], language: Annotated[str, Form()] = "auto"
) -> JSONResponse:
    ext = Path(file.filename or "video.mp4").suffix or ".mp4"
    UPLOADS.mkdir(parents=True, exist_ok=True)
    asset_id = uuid.uuid4().hex
    media_path = UPLOADS / f"{asset_id}{ext}"

    with open(media_path, "wb") as fh:
        while chunk := await file.read(1024 * 1024):
            fh.write(chunk)

    _reject_if_unreadable(media_path)

    def run(progress) -> Project:
        return transcribe_media(
            str(media_path), _provider, settings, language, progress=progress
        )

    job_id = await manager.submit(
        "transcribe",
        run,
        payload={"filename": file.filename, "language": language, "asset_id": asset_id},
    )
    return JSONResponse({"job_id": job_id, "asset_id": asset_id})


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str) -> JSONResponse:
    try:
        return JSONResponse(store.get(job_id))
    except KeyError:
        raise HTTPException(status_code=404, detail="job not found") from None


@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str) -> StreamingResponse:
    async def gen():
        last = None
        while True:
            try:
                data = store.get(job_id)
            except KeyError:
                yield "data: " + json.dumps({"error": "job not found"}) + "\n\n"
                return
            snapshot = json.dumps(data)
            if snapshot != last:
                last = snapshot
                yield f"data: {snapshot}\n\n"
            if data["status"] in ("done", "failed"):
                return
            await asyncio.sleep(0.5)

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/assets/{asset_id}")
async def get_asset(asset_id: str, request: Request) -> FileResponse:
    path = _asset_path(asset_id)
    if path is None:
        raise HTTPException(status_code=404, detail="asset not found")
    return FileResponse(
        path, media_type=_MEDIA_TYPES.get(path.suffix, "application/octet-stream")
    )


@app.post("/api/export/subtitles")
async def export_subtitles_route(payload: SubtitleRequest) -> PlainTextResponse:
    try:
        project = Project.model_validate(payload.project)
        text = export_subtitles(project, payload.format, settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PlainTextResponse(text, media_type="text/plain; charset=utf-8")


@app.post("/api/exports")
async def create_export(payload: ExportRequest) -> JSONResponse:
    if payload.format != "mp4":
        raise HTTPException(
            status_code=400, detail="use /api/export/subtitles for text formats"
        )
    source = _asset_path(payload.asset_id)
    if source is None:
        raise HTTPException(status_code=404, detail="asset not found")

    try:
        project = Project.model_validate(payload.project)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"invalid project: {exc}") from exc

    EXPORTS.mkdir(parents=True, exist_ok=True)
    export_id = uuid.uuid4().hex
    out_path = EXPORTS / f"{export_id}.mp4"
    opts = ExportOptions(
        aspect=payload.aspect, mode=payload.mode, crf=payload.crf, preset=payload.preset
    )

    def run(progress) -> dict:
        burn_video(
            settings,
            str(source),
            project,
            str(out_path),
            opts,
            progress=lambda frac: progress("export", {"frac": frac}),
        )
        return {"path": str(out_path)}

    job_id = await manager.submit("export", run, payload={"export_id": export_id})
    return JSONResponse({"job_id": job_id, "export_id": export_id})


@app.get("/api/exports/{export_id}/download")
async def download_export(export_id: str) -> FileResponse:
    path = EXPORTS / f"{export_id}.mp4"
    if not path.exists():
        raise HTTPException(status_code=404, detail="export not ready")
    return FileResponse(path, media_type="video/mp4", filename="vox-darija.mp4")
