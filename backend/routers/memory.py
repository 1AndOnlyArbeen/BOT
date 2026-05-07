"""Memory endpoints: facts, episodic, knowledge graph."""
from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from agent.learning import all_memories, forget_all, forget_one, remember
from agent import episodic, knowledge_graph as kg

router = APIRouter()

MAX_ENTRY_CHARS = 50_000             # split larger pastes/files into chunks of this size
                                     # (per-upload size cap removed — uploads are unbounded;
                                     # large files are still chunked into vector-store entries below)


class AddFact(BaseModel):
    text: str


class AddBulkText(BaseModel):
    text: str
    label: str = ""


class SearchBody(BaseModel):
    query: str
    k: int = 5


def _chunk(text: str, size: int = MAX_ENTRY_CHARS) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    out, cur = [], ""
    for para in text.split("\n\n"):
        if len(cur) + len(para) + 2 > size and cur:
            out.append(cur.strip())
            cur = ""
        cur += para + "\n\n"
    if cur.strip():
        out.append(cur.strip())
    final = []
    for c in out:
        if len(c) <= size:
            final.append(c)
        else:
            for i in range(0, len(c), size):
                final.append(c[i:i + size])
    return final


@router.get("/facts")
def facts() -> list[dict]:
    return all_memories()


@router.post("/facts")
def add_fact(body: AddFact) -> dict:
    n = remember([body.text])
    return {"saved": n}


@router.post("/facts/text")
def add_bulk_text(body: AddBulkText) -> dict:
    """Save a large free-text paste as one or more memory entries."""
    chunks = _chunk(body.text)
    if not chunks:
        raise HTTPException(400, "empty text")
    if body.label.strip():
        chunks = [f"[{body.label.strip()}] {c}" for c in chunks]
    n = remember(chunks)
    return {"saved": n, "chunks": len(chunks)}


@router.post("/facts/upload")
async def add_from_file(file: UploadFile = File(...), label: str = Form("")) -> dict:
    """Save the contents of an uploaded text file (txt/md/log/code/json/csv) as memory."""
    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = raw.decode("latin-1")
        except Exception:
            raise HTTPException(415, "could not decode file as text — upload UTF-8 / plain text only")
    chunks = _chunk(text)
    if not chunks:
        raise HTTPException(400, "file is empty")
    name = label.strip() or (file.filename or "file")
    chunks = [f"[file:{name}] {c}" for c in chunks]
    n = remember(chunks)
    return {"saved": n, "chunks": len(chunks), "filename": file.filename}


@router.delete("/facts")
def delete_fact(text: str) -> dict:
    return {"ok": forget_one(text)}


@router.delete("/facts/all")
def wipe_facts() -> dict:
    forget_all()
    return {"ok": True}


@router.post("/episodic/search")
def episodic_search(body: SearchBody) -> list[dict]:
    return episodic.recall_episodes(body.query, k=body.k)


@router.get("/episodic/stats")
def episodic_stats() -> dict:
    return episodic.stats()


@router.delete("/episodic")
def reset_episodic() -> dict:
    episodic.reset()
    return {"ok": True}


@router.get("/kg/entities")
def entities(limit: int = 50) -> list[dict]:
    return kg.list_entities(limit=limit)


@router.get("/kg/triples")
def triples(limit: int = 200) -> list[dict]:
    return kg.all_triples(limit=limit)


@router.get("/kg/query")
def query_entity(name: str) -> dict:
    return kg.query_entity(name)


@router.delete("/kg")
def reset_kg() -> dict:
    kg.reset()
    return {"ok": True}
