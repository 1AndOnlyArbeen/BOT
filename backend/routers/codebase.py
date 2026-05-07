"""Codebase RAG API: ingest zip/path, list repos, search, explain how-to."""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel

from agent import codebase as cb
from agent.codebase_tools import codebase_explain_how_to


router = APIRouter()


class SearchBody(BaseModel):
    query: str
    repo: str = ""
    k: int = 8


class ExplainBody(BaseModel):
    action: str
    repo: str = ""


class IngestPathBody(BaseModel):
    repo: str
    path: str


@router.get("/")
def list_all() -> list[dict]:
    return cb.list_repos()


@router.get("/files")
def files(repo: str) -> list[str]:
    return cb.list_repo_files(repo)


@router.post("/ingest-zip")
async def ingest_zip(repo: str = Form(...), file: UploadFile = File(...)) -> dict:
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(await file.read())
        path = tmp.name
    try:
        return cb.ingest_zip(repo, path)
    finally:
        Path(path).unlink(missing_ok=True)


@router.post("/ingest-path")
def ingest_path(body: IngestPathBody) -> dict:
    return cb.ingest_path(body.repo, body.path)


@router.post("/search")
def search(body: SearchBody) -> list[dict]:
    return cb.search_codebase(body.query, repo=body.repo, k=body.k)


@router.post("/explain")
def explain(body: ExplainBody) -> dict:
    text = codebase_explain_how_to.invoke({"action": body.action, "repo": body.repo})
    return {"explanation": text}


@router.delete("/{repo}")
def delete(repo: str) -> dict:
    return {"ok": cb.delete_repo(repo)}
