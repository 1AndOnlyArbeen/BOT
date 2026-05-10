"""Cross-turn recall — what the coder remembers from past work.

Three sources, all read-only here (writes happen via _persist_turn after
the chat router gets the final answer):

  - memory_context  → durable "User's X is Y" facts (agent.learning)
  - episodic_context → past turn snippets that match the query (agent.episodic)
  - kg_context      → entity/relationship triples (agent.knowledge_graph)

Plus the code library seeded with patterns from past wins:

  - relevant_patterns → top-N similar patterns from agent.code_library

Combined into one block the prompt builder injects after the project
primer. Caps the total size so context stays under control.
"""
from __future__ import annotations

from agent.learning import memory_context
from agent.episodic import episodic_context
from agent.knowledge_graph import kg_context
from agent.code_library import find_similar


MAX_BLOCK_CHARS = 2400


def _format_patterns(query: str, k: int = 3) -> str:
    """Pull top-k seeded/saved patterns and format for the system prompt."""
    try:
        hits = find_similar(query, k=k, min_score=0.0)
    except Exception:
        return ""
    if not hits:
        return ""

    parts = []
    for i, h in enumerate(hits, 1):
        req = (h.get("request") or "").strip()
        lang = (h.get("language") or "").strip() or "text"
        code = (h.get("code") or "").strip()
        if not req or not code:
            continue
        # Trim each pattern; the model just needs the gist + signature.
        if len(code) > 600:
            code = code[:600] + "\n# …(truncated; use search_code_library for full snippet)"
        parts.append(f"[{i}] use-case: {req}\n```{lang}\n{code}\n```")
    if not parts:
        return ""
    body = "\n\n".join(parts)
    return f"\n\n# Relevant patterns from your library (auto-recalled)\n{body}\n"


def build_recall_block(query: str) -> str:
    """Compose the full recall block. Empty string if nothing matched."""
    pieces: list[str] = []

    try:
        mem = memory_context(query)
    except Exception:
        mem = ""
    if mem.strip():
        pieces.append(mem.strip())

    try:
        epi = episodic_context(query, max_chars=600)
    except Exception:
        epi = ""
    if epi.strip():
        pieces.append(epi.strip())

    try:
        kg = kg_context(query)
    except Exception:
        kg = ""
    if kg.strip():
        pieces.append(kg.strip())

    patterns = _format_patterns(query)
    if patterns.strip():
        pieces.append(patterns.strip())

    if not pieces:
        return ""

    block = "\n\n".join(pieces)
    if len(block) > MAX_BLOCK_CHARS:
        block = block[:MAX_BLOCK_CHARS] + "\n…(recall truncated)"
    return "\n\n# Cross-turn recall\n" + block + "\n"


def recall_summary(query: str) -> dict:
    """Cheap summary for the cli_stage event — no full content, just counts.

    Returns: {"facts": int, "episodes": int, "kg_triples": int, "patterns": int}
    """
    try:
        from agent.learning import recall as recall_facts
        facts = len(recall_facts(query, k=5) or [])
    except Exception:
        facts = 0

    try:
        from agent.episodic import recall_episodes
        episodes = len(recall_episodes(query, k=3) or [])
    except Exception:
        episodes = 0

    try:
        # kg_context returns formatted text — count non-empty lines as a proxy.
        kg_text = kg_context(query)
        triples = len([ln for ln in kg_text.splitlines() if ln.strip().startswith("-")])
    except Exception:
        triples = 0

    try:
        patterns = len(find_similar(query, k=3, min_score=0.0) or [])
    except Exception:
        patterns = 0

    return {
        "facts": facts,
        "episodes": episodes,
        "kg_triples": triples,
        "patterns": patterns,
    }
