"""Long-term memory: extract facts about the user, recall relevant ones on new chats."""
from __future__ import annotations

import time
from functools import lru_cache

from langchain_chroma import Chroma
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.documents import Document

from config import (
    MEMORY_DIR, EMBED_MODEL, LLM_MODEL,
    MEMORY_TOP_K, MEMORY_AUTO_LEARN,
)


@lru_cache(maxsize=1)
def _store() -> Chroma:
    embeddings = OllamaEmbeddings(model=EMBED_MODEL)
    return Chroma(
        persist_directory=str(MEMORY_DIR),
        embedding_function=embeddings,
        collection_name="memories",
    )


@lru_cache(maxsize=1)
def _extractor():
    return ChatOllama(model=LLM_MODEL, temperature=0.1, num_predict=200)


EXTRACT_PROMPT = """From the exchange below, extract any DURABLE facts about the user.
Durable = preferences, identity, ongoing projects, skills, recurring goals.
Skip: ephemeral questions, one-off tasks, general knowledge.

Output ONE fact per line, starting with "User ".
If no durable facts, output exactly: NONE

EXCHANGE:
User: {user}
Assistant: {assistant}

FACTS:"""


def extract_facts(user_msg: str, assistant_msg: str) -> list[str]:
    """Use the LLM to pull durable facts out of a turn."""
    if not MEMORY_AUTO_LEARN:
        return []
    if len(user_msg) < 10:
        return []
    try:
        resp = _extractor().invoke(
            EXTRACT_PROMPT.format(user=user_msg[:1500], assistant=assistant_msg[:1500])
        ).content
    except Exception:
        return []

    import re
    cleaned = re.sub(r"<think>.*?</think>", "", resp, flags=re.DOTALL).strip()
    if "NONE" in cleaned.upper():
        return []
    facts = []
    for line in cleaned.split("\n"):
        line = line.strip().lstrip("-•*").strip()
        if line.lower().startswith("user ") and len(line) < 300:
            facts.append(line)
    return facts[:5]


def _is_duplicate(fact: str, threshold: float = 0.92) -> bool:
    """Check semantic similarity vs existing memories — avoid storing near-duplicates."""
    try:
        results = _store().similarity_search_with_score(fact, k=1)
    except Exception:
        return False
    if not results:
        return False
    doc, score = results[0]
    if doc.page_content.strip().lower() == fact.strip().lower():
        return True
    try:
        return float(score) <= (1.0 - threshold)
    except Exception:
        return False


def _reinforce(fact: str) -> bool:
    """Bump reinforcement counter on the matching memory if any."""
    try:
        meta = _store().get(include=["documents", "metadatas"])
        for i, doc in enumerate(meta["documents"]):
            if doc.strip().lower() == fact.strip().lower():
                m = meta["metadatas"][i] or {}
                m["reinforcements"] = int(m.get("reinforcements", 0)) + 1
                m["last_seen"] = time.time()
                _store().delete(ids=[meta["ids"][i]])
                _store().add_documents([Document(page_content=doc, metadata=m)])
                return True
    except Exception:
        pass
    return False


def remember(facts: list[str]) -> int:
    if not facts:
        return 0
    saved = 0
    for f in facts:
        if _is_duplicate(f):
            _reinforce(f)
            continue
        _store().add_documents([
            Document(
                page_content=f,
                metadata={"created_at": time.time(), "reinforcements": 0, "last_seen": time.time()},
            )
        ])
        saved += 1
    return saved


def recall(query: str, k: int = MEMORY_TOP_K) -> list[str]:
    if not query.strip():
        return []
    try:
        results = _store().similarity_search(query, k=k)
        return [d.page_content for d in results]
    except Exception:
        return []


def all_memories() -> list[dict]:
    try:
        meta = _store().get(include=["documents", "metadatas"])
        out = []
        for doc, m in zip(meta["documents"], meta["metadatas"]):
            out.append({"text": doc, "created_at": m.get("created_at", 0)})
        return sorted(out, key=lambda x: x["created_at"], reverse=True)
    except Exception:
        return []


def forget_all() -> None:
    try:
        _store().delete_collection()
    except Exception:
        pass
    _store.cache_clear()


def forget_one(text: str) -> bool:
    try:
        meta = _store().get(include=["documents"])
        for i, doc in enumerate(meta["documents"]):
            if doc == text:
                _store().delete(ids=[meta["ids"][i]])
                return True
    except Exception:
        pass
    return False


def memory_context(query: str) -> str:
    """Format recalled memories for injection into the system prompt."""
    mems = recall(query)
    if not mems:
        return ""
    lines = "\n".join(f"- {m}" for m in mems)
    return f"\n\nRELEVANT MEMORIES (things you've learned about this user):\n{lines}\n"


def learn_from_turn(user_msg: str, assistant_msg: str) -> list[str]:
    """One-shot: extract + remember. Returns saved facts."""
    facts = extract_facts(user_msg, assistant_msg)
    remember(facts)
    return facts
