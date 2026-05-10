"""Staged RAG pipeline.

The pipeline is intentionally split into small, single-purpose stages so each
one can be tuned (or replaced) without touching the rest:

    contextualize → rewrite follow-up turns into standalone search queries
    analyze       → classify the user's intent
    expand        → generate query variants for hard questions
    retrieve      → MMR vector search per variant
    rerank        → fuse + re-score by occurrence + position
    assemble      → format the chosen chunks into a citation-ready block
    reason        → stream the final answer with intent-tuned prompting

Each stage yields a `rag_stage` event the UI can render as a reasoning trace.
The shape is `{"type": "rag_stage", "data": {"name", "status", "summary", ...}}`.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Iterator, Literal

from langchain_ollama import ChatOllama

from rag.ingest import get_vectorstore
from config import LLM_MODEL, RETRIEVE_K


Intent = Literal["factoid", "comparative", "summary", "procedural", "off_topic"]


# --- Tunables --------------------------------------------------------------
#
# Kept here so the pipeline file is the one place to tweak retrieval behavior.
# `target_k` is per-intent because broad questions ("summarize…") want more
# coverage while factoids want precision.

K_BY_INTENT: dict[Intent, int] = {
    "factoid": 4,
    "procedural": 6,
    "comparative": 8,
    "summary": 10,
    "off_topic": 0,
}

CHAR_BUDGET_BY_INTENT: dict[Intent, int] = {
    "factoid": 1500,
    "procedural": 2200,
    "comparative": 2800,
    "summary": 3500,
    "off_topic": 0,
}

# MMR settings: fetch a wider pool, then diversify down to k.
MMR_FETCH_MULT = 4
MMR_LAMBDA = 0.55  # 0 = max diversity, 1 = pure relevance

# Cap query variants to keep retrieval latency bounded on local LLMs.
MAX_VARIANTS = 3


# --- History-aware contextualization ---------------------------------------
#
# Follow-up turns ("what about latency?", "tell me more", "and the second one?")
# are useless for retrieval on their own — they reference subjects from earlier
# turns the vector store has never seen. We rewrite them into standalone search
# queries before analyze/expand/retrieve. The user's *original* message is kept
# verbatim for the final answer so the model still answers what they actually
# asked, in their own words.
#
# Cheap heuristic first — only call the LLM when a turn looks like a follow-up
# (pronouns, short, or starts with a continuation word). Keeps the common case
# fast on a local model.

_FOLLOWUP_RE = re.compile(
    r"\b(it|its|they|them|their|those|these|this|that|"
    r"the\s+(?:first|second|third|fourth|fifth|last|other|next|previous|same|former|latter))\b|"
    r"^\s*(and|also|but|so|then|why|how|what|tell\s+me|more|"
    r"what\s+about|how\s+about|what\s+if)\b",
    re.IGNORECASE,
)

_CONTEXTUALIZE_SYSTEM = (
    "You receive a conversation between a user and an assistant, and the user's "
    "LATEST message. Rewrite that latest message as a STANDALONE search query "
    "that captures the full intent, resolving any pronouns or references using "
    "the prior turns. If the message is already standalone, output it unchanged. "
    "Output ONLY the rewritten query — one line, no quotes, no commentary, "
    "no leading 'Search:' label."
)


def _looks_like_followup(message: str, history: list[dict]) -> bool:
    if not history:
        return False
    msg = (message or "").strip()
    if not msg:
        return False
    if len(msg.split()) <= 4:
        return True
    return bool(_FOLLOWUP_RE.search(msg))


def contextualize(message: str, history: list[dict] | None) -> str:
    """Rewrite a follow-up turn into a standalone query using recent history."""
    if not history or not _looks_like_followup(message, history):
        return message

    recent = [m for m in history[-6:] if m.get("role") in ("user", "assistant")]
    if not recent:
        return message

    convo = "\n".join(
        f"{m['role']}: {str(m.get('content', ''))[:400]}" for m in recent
    )
    user_block = (
        f"Conversation so far:\n{convo}\n\n"
        f"Latest user message: {message}\n\n"
        f"Standalone search query:"
    )
    try:
        llm = ChatOllama(model=LLM_MODEL, temperature=0.1, num_predict=80, num_ctx=1024)
        out = llm.invoke([("system", _CONTEXTUALIZE_SYSTEM), ("user", user_block)]).content
    except Exception:
        return message

    rewritten = (out or "").strip().splitlines()[0].strip() if out else ""
    rewritten = rewritten.strip().strip('"').strip("'").strip()
    rewritten = re.sub(r"^(?:standalone\s+)?(?:search\s+)?query[:\-]\s*", "", rewritten, flags=re.IGNORECASE)
    if not rewritten or len(rewritten) > 300 or len(rewritten) < 3:
        return message
    return rewritten


# --- Heuristic intent classifier -------------------------------------------
#
# Heuristics first (no LLM) — only fall back to a tiny LLM judge when none of
# the patterns match. This keeps the common case fast on a local model.

_OFF_TOPIC_PATTERNS = (
    r"\bweather\b", r"\btime\b", r"\bopen\s+\w+", r"\bplay\s+\w+",
    r"\bjoke\b", r"\bremind\s+me\b", r"\bcalculator?\b", r"\bcalculate\b",
    r"^\s*(hi|hello|hey|yo|sup)\b",
)
_COMPARATIVE_RE = re.compile(
    r"\b(compare|versus|vs\.?|difference|differences|differ|"
    r"better|worse|pros\s+and\s+cons|tradeoffs?)\b",
    re.IGNORECASE,
)
_SUMMARY_RE = re.compile(
    r"\b(summari[sz]e|summary|overview|tl;?dr|in\s+short|key\s+points|"
    r"main\s+(?:ideas?|points?|takeaways?))\b",
    re.IGNORECASE,
)
_PROCEDURAL_RE = re.compile(
    r"\b(how\s+(?:do|to|can|should)|steps?|procedure|walk\s+me\s+through|"
    r"setup|configure|install|guide)\b",
    re.IGNORECASE,
)


@dataclass
class Analysis:
    intent: Intent
    target_k: int
    char_budget: int
    needs_expansion: bool

    @property
    def summary(self) -> str:
        return f"intent={self.intent} k={self.target_k} expand={self.needs_expansion}"


def analyze(query: str) -> Analysis:
    """Classify the query into an intent without touching the LLM."""
    q = (query or "").strip()
    low = q.lower()

    if not q or any(re.search(p, low) for p in _OFF_TOPIC_PATTERNS):
        if not q or len(q) < 5:
            return Analysis("off_topic", 0, 0, False)

    if _COMPARATIVE_RE.search(q):
        intent: Intent = "comparative"
    elif _SUMMARY_RE.search(q):
        intent = "summary"
    elif _PROCEDURAL_RE.search(q):
        intent = "procedural"
    else:
        intent = "factoid"

    return Analysis(
        intent=intent,
        target_k=K_BY_INTENT[intent],
        char_budget=CHAR_BUDGET_BY_INTENT[intent],
        needs_expansion=intent in ("comparative", "summary", "procedural"),
    )


# --- Query expansion -------------------------------------------------------

_EXPANSION_SYSTEM = (
    "You rewrite a user question into 2 short alternative search queries that "
    "would pull DIFFERENT but relevant passages from a document store. "
    "Output ONE alternative per line. No numbering, no quotes, no commentary. "
    "Each alternative must stay on the same topic — paraphrase or zoom in."
)


def expand(query: str, analysis: Analysis) -> list[str]:
    """Return a list of search queries — original first, then variants."""
    if not analysis.needs_expansion:
        return [query]

    try:
        llm = ChatOllama(model=LLM_MODEL, temperature=0.4, num_predict=120, num_ctx=1024)
        out = llm.invoke([("system", _EXPANSION_SYSTEM), ("user", query)]).content
    except Exception:
        return [query]

    variants: list[str] = []
    for line in (out or "").splitlines():
        line = line.strip().strip('-•*').strip().strip('"').strip()
        if not line or line.lower() == query.lower().strip():
            continue
        # Drop leading numbering like "1." or "(2)"
        line = re.sub(r"^\(?\d+\)?[.)\s-]+", "", line).strip()
        if 5 <= len(line) <= 200:
            variants.append(line)
        if len(variants) >= MAX_VARIANTS - 1:
            break
    return [query] + variants


# --- Retrieval -------------------------------------------------------------

@dataclass
class Hit:
    """One retrieved chunk + bookkeeping for ranking and citations."""
    content: str
    source: str
    page: str | int | None
    matched_queries: set[str] = field(default_factory=set)
    rank_sum: int = 0  # lower is better (sum of positions across variants)

    @property
    def key(self) -> str:
        # Stable dedup key — same source+content collapses to one hit even if
        # two query variants both pulled it.
        h = hashlib.md5(self.content[:400].encode("utf-8")).hexdigest()[:12]
        return f"{self.source}|{h}"

    @property
    def location(self) -> str:
        if self.page not in (None, ""):
            return f"{self.source} p.{self.page}"
        return self.source


def _vs_search(query: str, k: int) -> list:
    vs = get_vectorstore()
    fetch_k = max(k * MMR_FETCH_MULT, 8)
    try:
        return vs.max_marginal_relevance_search(
            query, k=k, fetch_k=fetch_k, lambda_mult=MMR_LAMBDA,
        )
    except Exception:
        try:
            return vs.similarity_search(query, k=k)
        except Exception:
            return []


def retrieve(queries: list[str], k: int) -> dict[str, Hit]:
    """Pool hits across every query variant. Dedupe by source+content hash."""
    pool: dict[str, Hit] = {}
    for q in queries:
        docs = _vs_search(q, k=k)
        for pos, d in enumerate(docs):
            hit = Hit(
                content=d.page_content.strip(),
                source=d.metadata.get("source", "unknown"),
                page=d.metadata.get("page", ""),
            )
            existing = pool.get(hit.key)
            if existing is None:
                hit.matched_queries.add(q)
                hit.rank_sum = pos
                pool[hit.key] = hit
            else:
                existing.matched_queries.add(q)
                existing.rank_sum += pos
    return pool


# --- Reranking -------------------------------------------------------------
#
# Reciprocal-rank-fusion-ish: chunks retrieved by multiple variants get a
# bonus, and lower aggregate position is better. Cheap and fully offline —
# no extra LLM judge call.

def rerank(pool: dict[str, Hit], target_k: int) -> list[Hit]:
    items = list(pool.values())

    def score(h: Hit) -> tuple[int, int]:
        # First key (descending): how many variants matched it.
        # Second key (ascending): aggregate rank — lower means it appeared
        # closer to the top in each retrieval.
        return (-len(h.matched_queries), h.rank_sum)

    items.sort(key=score)
    return items[:target_k]


# --- Context assembly ------------------------------------------------------

def assemble(hits: list[Hit], char_budget: int) -> tuple[str, list[Hit]]:
    """Format hits into a numbered citation block. Returns (block, kept_hits)."""
    if not hits:
        return "", []

    parts: list[str] = []
    kept: list[Hit] = []
    used = 0
    for i, h in enumerate(hits, 1):
        snippet = h.content
        chunk = f"[{i}] ({h.location})\n{snippet}"
        if used + len(chunk) > char_budget and kept:
            break
        parts.append(chunk)
        kept.append(h)
        used += len(chunk) + 2  # account for "\n\n" join

    block = "\n\n".join(parts)
    return block, kept


# --- Reasoning -------------------------------------------------------------

_BASE_RULES = (
    "Answer ONLY from the RELEVANT DOCUMENTS block. Do NOT use general or world "
    "knowledge to fill gaps. If the documents don't contain the answer, reply "
    "exactly: \"I can't find that in your RAG corpus. Try rephrasing, or upload "
    "a relevant document.\" Cite EVERY claim inline as `[1]`, `[2]`, … matching "
    "the chunk numbers. End with a `Sources:` line listing the cited indices "
    "and source labels. Plain prose only — no JSON, no tool calls."
)

_INTENT_GUIDANCE: dict[Intent, str] = {
    "factoid": (
        "Lead with the direct answer in 1–2 sentences, then 1–2 sentences of "
        "supporting detail from the chunks. Be precise."
    ),
    "procedural": (
        "Lay the answer out as a numbered list of steps drawn from the chunks. "
        "Each step gets a citation. End with any prerequisites or gotchas the "
        "documents call out."
    ),
    "comparative": (
        "Structure the answer as a short side-by-side comparison: a paragraph "
        "per option / item, then a final paragraph naming the meaningful "
        "differences. Cite each claim."
    ),
    "summary": (
        "Open with a one-paragraph executive summary, then 4–6 bullet points "
        "covering the main themes. Be comprehensive across the cited chunks."
    ),
    "off_topic": "",
}

_REFUSAL = (
    "This is the RAG chat — I only answer from documents you've uploaded. "
    "Switch to Chat / Coder / Ultron mode for general questions."
)


def _build_system_prompt(analysis: Analysis, context: str) -> str:
    return (
        f"# Role\nYou are the user's RAG assistant for the {analysis.intent} "
        f"question they just asked.\n\n"
        f"# Hard rules\n{_BASE_RULES}\n\n"
        f"# How to answer\n{_INTENT_GUIDANCE[analysis.intent]}\n\n"
        f"# Reasoning\nThink briefly inside <think> tags about which chunks "
        f"actually support the answer; keep that reasoning under 80 words. "
        f"Then write the final answer outside the tags. Only the final answer "
        f"is shown to the user.\n\n"
        f"RELEVANT DOCUMENTS (cite as [1], [2], …):\n{context}\n"
    )


# --- Orchestrator ----------------------------------------------------------

def _vectorstore_empty() -> bool:
    try:
        vs = get_vectorstore()
        return (vs._collection.count() if hasattr(vs, "_collection") else 0) == 0
    except Exception:
        return False


def _stage_event(name: str, status: str, summary: str, **detail) -> dict:
    return {
        "type": "rag_stage",
        "data": {"name": name, "status": status, "summary": summary, **detail},
    }


def run(message: str, history: list[dict] | None = None) -> Iterator[dict]:
    """Run the full pipeline. Yields events suitable for SSE streaming.

    Event types yielded:
      - router       (compat with the existing UI)
      - rag_stage    (one per pipeline stage; status=running|done)
      - tool_call    (rag_search marker — keeps the legacy UI happy)
      - tool_result  (the assembled chunk block)
      - token        (running answer)
      - final        (full final answer)
      - error        (anything raised inside a stage)
    """
    yield {"type": "router", "data": {"categories": ["rag"], "tool_count": 0}}

    if _vectorstore_empty():
        msg = (
            "Your RAG corpus is empty. Upload files or paste text on the RAG "
            "tab and then ask again."
        )
        yield _stage_event("retrieve", "done", "corpus empty", count=0)
        yield {"type": "token", "data": msg}
        yield {"type": "final", "data": msg}
        return

    # 0. contextualize — resolve pronouns / follow-ups using recent history
    search_query = message
    if history:
        yield _stage_event("contextualize", "running", "rewriting follow-up with history…")
        search_query = contextualize(message, history)
        if search_query == message:
            yield _stage_event(
                "contextualize", "done", "standalone — no rewrite needed",
                rewritten=search_query, original=message,
            )
        else:
            yield _stage_event(
                "contextualize", "done",
                f"rewrote → {search_query[:90]}",
                rewritten=search_query, original=message,
            )

    # 1. analyze (use the contextualized query so short follow-ups aren't off-topic)
    analysis = analyze(search_query)
    yield _stage_event(
        "analyze", "done", analysis.summary,
        intent=analysis.intent, target_k=analysis.target_k,
    )

    if analysis.intent == "off_topic":
        yield {"type": "token", "data": _REFUSAL}
        yield {"type": "final", "data": _REFUSAL}
        return

    # 2. expand
    yield _stage_event("expand", "running", "rewriting query…")
    queries = expand(search_query, analysis)
    yield _stage_event(
        "expand", "done",
        f"{len(queries)} query variant{'s' if len(queries) != 1 else ''}",
        variants=queries,
    )

    # 3. retrieve
    yield _stage_event("retrieve", "running", f"MMR top-{analysis.target_k}…")
    pool = retrieve(queries, k=analysis.target_k)
    sources_seen = sorted({h.source for h in pool.values()})
    yield _stage_event(
        "retrieve", "done",
        f"{len(pool)} chunks across {len(sources_seen)} sources",
        count=len(pool), sources=sources_seen,
    )

    if not pool:
        msg = (
            "I can't find that in your RAG corpus. Try rephrasing, or upload "
            "a relevant document on the RAG tab."
        )
        yield {"type": "token", "data": msg}
        yield {"type": "final", "data": msg}
        return

    # 4. rerank
    ranked = rerank(pool, target_k=analysis.target_k)
    yield _stage_event(
        "rerank", "done",
        f"kept top {len(ranked)} by fusion score",
        kept=[
            {
                "index": i + 1,
                "label": h.location,
                "matches": len(h.matched_queries),
            }
            for i, h in enumerate(ranked)
        ],
    )

    # 5. assemble — also emit legacy tool_call/tool_result so the existing
    # citation chip strip in the UI keeps working.
    block, kept = assemble(ranked, char_budget=analysis.char_budget)
    yield {"type": "tool_call", "data": {"name": "rag_search", "args": search_query[:120]}}
    yield {"type": "tool_result", "data": {"name": "rag_search", "content": block[:600]}}
    yield _stage_event(
        "assemble", "done",
        f"{len(kept)} chunks · {len(block)} chars",
        chars=len(block),
    )

    # 6. reason — stream tokens.
    yield _stage_event("reason", "running", "thinking…")
    sys_prompt = _build_system_prompt(analysis, block)

    msgs: list[tuple[str, str]] = [("system", sys_prompt)]
    for m in (history or [])[-6:]:
        msgs.append((m["role"], m["content"]))
    msgs.append(("user", message))

    llm = ChatOllama(
        model=LLM_MODEL,
        temperature=0.2,
        num_predict=1400,
        num_ctx=4096,
    )

    final_text = ""
    try:
        for chunk in llm.stream(msgs):
            piece = getattr(chunk, "content", "") or ""
            if not piece:
                continue
            final_text += piece
            yield {"type": "token", "data": _strip_thinking(final_text)}
    except Exception as e:
        yield {"type": "error", "data": f"rag reply failed: {e}"}
        return

    final_text = _strip_thinking(final_text).strip() or (
        "I can't find that in your RAG corpus. Try rephrasing, or upload a "
        "relevant document on the RAG tab."
    )
    yield _stage_event("reason", "done", "answer ready", length=len(final_text))
    yield {"type": "final", "data": final_text}


_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def _strip_thinking(text: str) -> str:
    return _THINK_RE.sub("", text or "").strip()
