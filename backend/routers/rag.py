"""RAG: shared corpus across chat/coder/ultron. Accepts any file or raw text."""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException
from pydantic import BaseModel

from rag.ingest import (
    ingest_files,
    ingest_text,
    list_sources,
    delete_source,
    reset_vectorstore,
)
from config import DOCS_DIR

router = APIRouter()


class IngestTextBody(BaseModel):
    text: str
    source: str = "pasted"


_SAFE = re.compile(r"[^A-Za-z0-9._\- ]+")


def _safe_filename(name: str) -> str:
    cleaned = _SAFE.sub("_", name).strip().strip(".")
    return cleaned or "upload"


@router.post("/upload")
async def upload(files: list[UploadFile] = File(...)) -> dict:
    """Save any number of files (any type) and ingest. No size limit."""
    saved: list[Path] = []
    for f in files:
        name = _safe_filename(f.filename or "upload")
        dest = DOCS_DIR / name
        dest.write_bytes(await f.read())
        saved.append(dest)
    chunks = ingest_files(saved)
    return {"chunks": chunks, "files": [s.name for s in saved]}


@router.post("/text")
def upload_text(body: IngestTextBody) -> dict:
    """Ingest raw text of arbitrary length under a source label."""
    if not body.text.strip():
        raise HTTPException(400, "text is empty")
    chunks = ingest_text(body.text, source=_safe_filename(body.source))
    return {"chunks": chunks, "source": _safe_filename(body.source)}


@router.get("/sources")
def sources() -> list[str]:
    return list_sources()


@router.delete("/source")
def remove_source(name: str) -> dict:
    deleted = delete_source(name)
    return {"ok": True, "deleted": deleted}


@router.delete("/sources")
def reset() -> dict:
    reset_vectorstore()
    return {"ok": True}
