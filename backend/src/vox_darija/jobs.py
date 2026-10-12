"""In-process job queue with a SQLite-backed store.

Simple and boring: transcription/export jobs run in a thread pool, progress is
written to SQLite (thread-safe), and the API streams progress over SSE by
polling the store.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import threading
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .schema import Project


class JobStore:
    def __init__(self, path: Path):
        self._lock = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                status TEXT NOT NULL,
                stage TEXT,
                progress REAL NOT NULL DEFAULT 0,
                payload TEXT,
                result TEXT,
                error TEXT,
                created_at REAL,
                updated_at REAL
            )
            """
        )
        self._conn.commit()

    def create(self, kind: str, payload: dict | None = None) -> str:
        job_id = uuid.uuid4().hex
        now = time.time()
        with self._lock:
            self._conn.execute(
                "INSERT INTO jobs (id, kind, status, stage, progress, payload, created_at, updated_at) "
                "VALUES (?, ?, 'queued', NULL, 0, ?, ?, ?)",
                (job_id, kind, json.dumps(payload or {}), now, now),
            )
            self._conn.commit()
        return job_id

    def update(self, job_id: str, **fields: Any) -> None:
        if not fields:
            return
        fields["updated_at"] = time.time()
        cols = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [job_id]
        with self._lock:
            self._conn.execute(f"UPDATE jobs SET {cols} WHERE id = ?", values)
            self._conn.commit()

    def get(self, job_id: str) -> dict:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, kind, status, stage, progress, payload, result, error, created_at, updated_at "
                "FROM jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
        if row is None:
            raise KeyError(job_id)
        keys = [
            "id",
            "kind",
            "status",
            "stage",
            "progress",
            "payload",
            "result",
            "error",
            "created_at",
            "updated_at",
        ]
        data = dict(zip(keys, row, strict=False))
        data["payload"] = json.loads(data["payload"] or "{}")
        data["result"] = json.loads(data["result"]) if data["result"] else None
        return data


class JobManager:
    def __init__(self, store: JobStore, max_workers: int = 2):
        self.store = store
        self.max_workers = max_workers
        self._queue: asyncio.Queue[
            tuple[str, Callable[[Callable[[str, dict], None]], Any]]
        ] = asyncio.Queue()
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        if not self._tasks:
            self._tasks = [
                asyncio.create_task(self._worker()) for _ in range(self.max_workers)
            ]

    async def shutdown(self) -> None:
        for task in self._tasks:
            task.cancel()
        self._tasks = []

    async def submit(
        self,
        kind: str,
        run_fn: Callable[[Callable[[str, dict], None]], Any],
        payload: dict | None = None,
    ) -> str:
        job_id = self.store.create(kind, payload)
        await self._queue.put((job_id, run_fn))
        return job_id

    async def _worker(self) -> None:
        while True:
            job_id, run_fn = await self._queue.get()
            self.store.update(job_id, status="running", progress=0.0)
            try:

                def progress(stage: str, info: dict, _job_id: str = job_id) -> None:
                    frac = _stage_progress(stage, info)
                    self.store.update(_job_id, stage=stage, progress=frac)

                result = await asyncio.to_thread(run_fn, progress)
                if isinstance(result, Project):
                    result = json.loads(result.model_dump_json())
                self.store.update(
                    job_id,
                    status="done",
                    stage="done",
                    progress=1.0,
                    result=json.dumps(result),
                )
            except Exception as exc:  # noqa: BLE001
                self.store.update(job_id, status="failed", error=str(exc))


def _stage_progress(stage: str, info: dict) -> float:
    if stage == "extract":
        return 0.1
    if stage == "vad":
        return 0.15
    if stage == "transcribe":
        total = info.get("total", 1) or 1
        return 0.15 + 0.7 * (info.get("index", 0) + 1) / total
    if stage == "segment":
        return 0.9
    if stage == "done":
        return 1.0
    if stage == "export":
        return float(info.get("frac", 0.0))
    return 0.0
