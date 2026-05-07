"""Code learning library — saves successful code patterns, retrieves on similar requests.

Workflow when user asks for code:
1. semantic search the library for similar past code → reuse if good
2. if nothing close, search web docs (DuckDuckGo + scrape top result)
3. write new code, run/verify, then save to library tagged with the original request

The library is a vector store keyed on the user request; payload includes code + language + outcome."""
from __future__ import annotations

import re
import time
from functools import lru_cache

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document
from langchain_core.tools import tool

from config import DATA_DIR, EMBED_MODEL


CODE_DIR = DATA_DIR / "code_library"
CODE_DIR.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def _store() -> Chroma:
    return Chroma(
        persist_directory=str(CODE_DIR),
        embedding_function=OllamaEmbeddings(model=EMBED_MODEL),
        collection_name="code_patterns",
    )


def save_pattern(request: str, code: str, language: str = "python", success: bool = True, notes: str = "") -> int:
    """Save a working code pattern indexed by the natural-language request that produced it."""
    if not request.strip() or not code.strip():
        return 0
    text = f"REQUEST: {request}\nLANGUAGE: {language}\nNOTES: {notes}\nCODE:\n{code}"
    doc = Document(
        page_content=text,
        metadata={
            "request": request[:300],
            "language": language,
            "success": int(success),
            "ts": time.time(),
            "notes": notes[:300],
        },
    )
    _store().add_documents([doc])
    return 1


def find_similar(request: str, k: int = 3, min_score: float = 0.0) -> list[dict]:
    if not request.strip():
        return []
    try:
        results = _store().similarity_search_with_score(request, k=k)
    except Exception:
        return []
    out = []
    for doc, score in results:
        out.append({
            "request": doc.metadata.get("request", ""),
            "language": doc.metadata.get("language", ""),
            "code": _extract_code(doc.page_content),
            "score": float(score),
            "ts": doc.metadata.get("ts", 0),
        })
    return out


def _extract_code(text: str) -> str:
    m = re.search(r"CODE:\n(.*)", text, re.DOTALL)
    return m.group(1).strip() if m else text


@tool
def search_code_library(request: str) -> str:
    """Search past code patterns YOU have written for THIS user. Always check here BEFORE searching the web —
    if you've solved a similar request before, reuse the pattern."""
    hits = find_similar(request, k=3)
    if not hits:
        return "(no similar past code)"
    out = []
    for i, h in enumerate(hits, 1):
        out.append(
            f"[{i}] {h['language']} — past request: {h['request']}\n"
            f"```{h['language']}\n{h['code'][:1500]}\n```"
        )
    return "\n\n".join(out)


@tool
def save_code_pattern(request: str, code: str, language: str = "python", notes: str = "") -> str:
    """After writing & verifying code that solves a user request, save it for future reuse.
    request: the original natural-language ask; code: the final working code; language: python/js/etc."""
    n = save_pattern(request, code, language=language, notes=notes)
    return f"✓ saved code pattern" if n else "[error] could not save"


@tool
def search_web_docs(library: str, topic: str) -> str:
    """Search the web specifically for programming-language docs on a topic.
    library: 'python', 'react', 'fastapi', 'pandas', etc. topic: what you need to know."""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return "[error] duckduckgo-search not installed"
    query = f"{library} {topic} site:docs OR site:github.com docs"
    try:
        with DDGS() as ddgs:
            hits = list(ddgs.text(query, max_results=5))
    except Exception as e:
        return f"[web error] {e}"
    if not hits:
        with DDGS() as ddgs:
            hits = list(ddgs.text(f"{library} {topic} documentation", max_results=5))
    if not hits:
        return "(no doc results)"
    return "\n\n".join(
        f"[{i}] {h.get('title','')}\n{h.get('href','')}\n{h.get('body','')}"
        for i, h in enumerate(hits, 1)
    )


CODE_LIBRARY_TOOLS = [search_code_library, save_code_pattern, search_web_docs]


def list_all() -> list[dict]:
    try:
        meta = _store().get(include=["documents", "metadatas"])
        return [
            {"request": m.get("request", ""), "language": m.get("language", ""), "ts": m.get("ts", 0)}
            for m in meta["metadatas"]
        ]
    except Exception:
        return []
