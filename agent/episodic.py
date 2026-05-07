"""Episodic memory — embed full conversations into a vector store. Recall past chats."""
from __future__ import annotations

import time
from functools import lru_cache

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document

from config import DATA_DIR, EMBED_MODEL


EPISODIC_DIR = DATA_DIR / "episodic"
EPISODIC_DIR.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def _store() -> Chroma:
    return Chroma(
        persist_directory=str(EPISODIC_DIR),
        embedding_function=OllamaEmbeddings(model=EMBED_MODEL),
        collection_name="episodes",
    )


def archive_turn(session_id: int, user_msg: str, assistant_msg: str) -> None:
    """Archive a user+assistant exchange so it can be recalled later."""
    if not user_msg.strip() or len(user_msg) < 6:
        return
    text = f"User: {user_msg}\n\nAssistant: {assistant_msg}"
    doc = Document(
        page_content=text,
        metadata={"session_id": session_id, "ts": time.time(), "kind": "exchange"},
    )
    try:
        _store().add_documents([doc])
    except Exception:
        pass


def recall_episodes(query: str, k: int = 3) -> list[dict]:
    """Find past conversations relevant to a new query."""
    if not query.strip():
        return []
    try:
        results = _store().similarity_search_with_score(query, k=k)
    except Exception:
        return []
    out = []
    for doc, score in results:
        out.append({
            "text": doc.page_content,
            "session_id": doc.metadata.get("session_id"),
            "ts": doc.metadata.get("ts", 0),
            "score": float(score),
        })
    return out


def episodic_context(query: str, max_chars: int = 1200) -> str:
    """Format recalled episodes for prompt injection."""
    eps = recall_episodes(query, k=3)
    if not eps:
        return ""
    parts = []
    for e in eps:
        snippet = e["text"][:400]
        parts.append(f"- {snippet}")
    block = "\n\n".join(parts)[:max_chars]
    return f"\n\nRELEVANT PAST CONVERSATIONS:\n{block}\n"


def reset() -> None:
    try:
        _store().delete_collection()
    except Exception:
        pass
    _store.cache_clear()


def stats() -> dict:
    try:
        meta = _store().get()
        return {"count": len(meta.get("documents", []))}
    except Exception:
        return {"count": 0}
