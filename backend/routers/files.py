"""Files: workspace listing, file CRUD, document RAG ingest."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from agent.file_tools import list_workspace_tree
from rag.ingest import ingest_files, list_sources, reset_vectorstore
from config import WORKSPACE_DIR, DOCS_DIR

router = APIRouter()


class WriteFileBody(BaseModel):
    path: str
    content: str


def _resolve_workspace(rel: str) -> Path:
    rel_path = Path(rel.lstrip("/"))
    full = (WORKSPACE_DIR / rel_path).resolve()
    if not str(full).startswith(str(WORKSPACE_DIR.resolve())):
        raise HTTPException(400, "path escapes workspace")
    return full


@router.get("/tree")
def tree() -> list[dict]:
    return [{"path": p, "is_dir": d} for p, d in list_workspace_tree(max_depth=4)]


@router.get("/read")
def read(path: str) -> dict:
    full = _resolve_workspace(path)
    if not full.exists() or not full.is_file():
        raise HTTPException(404, "not found")
    try:
        return {"path": path, "content": full.read_text(encoding="utf-8")}
    except UnicodeDecodeError:
        raise HTTPException(400, "binary file")


@router.put("/write")
def write(body: WriteFileBody) -> dict:
    from agent.backup import snapshot
    full = _resolve_workspace(body.path)
    full.parent.mkdir(parents=True, exist_ok=True)
    if full.exists():
        snapshot(full, op="ui-write")
    full.write_text(body.content, encoding="utf-8")
    return {"ok": True, "size": len(body.content)}


@router.delete("/")
def delete(path: str) -> dict:
    from agent.backup import snapshot
    full = _resolve_workspace(path)
    if not full.exists():
        raise HTTPException(404, "not found")
    if full.is_dir():
        raise HTTPException(400, "is a directory")
    snapshot(full, op="ui-delete")
    full.unlink()
    return {"ok": True}


@router.post("/upload-docs")
async def upload_docs(files: list[UploadFile] = File(...)) -> dict:
    saved = []
    for f in files:
        dest = DOCS_DIR / f.filename
        dest.write_bytes(await f.read())
        saved.append(dest)
    chunks = ingest_files(saved)
    return {"chunks": chunks, "files": [str(s.name) for s in saved]}


@router.get("/sources")
def sources() -> list[str]:
    return list_sources()


@router.delete("/sources")
def reset_sources() -> dict:
    reset_vectorstore()
    return {"ok": True}
