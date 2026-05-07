"""Agent tools for talking to the indexed codebase.

Workflow when user asks 'how do I create an order?':
1. codebase_search(query, repo) → top relevant chunks across the repo
2. codebase_explain_how_to(action, repo) → reads top chunks + synthesizes the recipe
3. codebase_show_file(path, repo) → drill into a specific file"""
from __future__ import annotations

import re

from langchain_core.tools import tool
from langchain_ollama import ChatOllama

from agent.codebase import (
    search_codebase, list_repos, list_repo_files, ingest_path, ingest_zip,
)
from config import LLM_MODEL


def _format_hits(hits: list[dict], max_chars: int = 4000) -> str:
    if not hits:
        return "(no matching code found — repo may not be indexed)"
    parts = []
    used = 0
    for i, h in enumerate(hits, 1):
        block = (
            f"\n--- [{i}] {h['path']}"
            + (f"  ({h['symbol']})" if h.get("symbol") else "")
            + f"  score={h['score']:.3f} ---\n"
            + h["content"]
        )
        if used + len(block) > max_chars:
            break
        parts.append(block)
        used += len(block)
    return "\n".join(parts)


@tool
def codebase_search(query: str, repo: str = "") -> str:
    """Search the indexed codebase. query: natural language ('how to create order'). repo: optional name to scope. Returns top code chunks with file paths."""
    hits = search_codebase(query, repo=repo, k=8)
    return _format_hits(hits)


@tool
def codebase_list_repos() -> str:
    """List indexed codebases the user has uploaded."""
    rs = list_repos()
    if not rs:
        return "(no codebases indexed yet)"
    return "\n".join(f"{r['repo']}  ·  {r['files']} files  ·  {r['chunks']} chunks" for r in rs)


@tool
def codebase_list_files(repo: str) -> str:
    """List all files in an indexed codebase."""
    fs = list_repo_files(repo)
    if not fs:
        return f"(no files indexed for repo '{repo}')"
    return "\n".join(fs[:200]) + (f"\n... ({len(fs)} total)" if len(fs) > 200 else "")


@tool
def codebase_show_file(path: str, repo: str = "") -> str:
    """Pull all chunks for a specific file path from the indexed codebase."""
    hits = search_codebase(f"FILE: {path}", repo=repo, k=20)
    same = [h for h in hits if h["path"] == path]
    if not same:
        return f"(no indexed content for {path})"
    return _format_hits(sorted(same, key=lambda h: h["chunk"]), max_chars=8000)


_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)


@tool
def codebase_explain_how_to(action: str, repo: str = "") -> str:
    """Explain HOW TO do something in this codebase by reading the actual code.
    Example: codebase_explain_how_to('create an order'). Returns step-by-step + code refs.
    USE THIS when the user asks 'how do I X?' about their indexed code."""
    hits = search_codebase(action, repo=repo, k=10)
    if not hits:
        return "(no relevant code — make sure the repo is indexed)"

    code_context = _format_hits(hits, max_chars=4500)
    prompt = f"""You are explaining HOW TO do something using ONLY the actual code shown below from the user's project.

USER ACTION: {action}

RELEVANT CODE FROM THE PROJECT:
{code_context}

Write a clear, concrete answer:
1. Overview: 1-2 sentences on the architecture path for this action.
2. Step-by-step: numbered steps the user would follow, referencing the actual files & function names from above.
3. Example: minimal code snippet they could adapt (use real names from above; do NOT invent function names).

Be specific. Cite file paths in backticks. Don't speculate beyond what the code shows.

Answer:"""

    try:
        llm = ChatOllama(model=LLM_MODEL, temperature=0.1, num_predict=900)
        resp = llm.invoke(prompt).content
        return _THINK.sub("", resp).strip()
    except Exception as e:
        return f"[error] {e}\n\nRaw findings:\n{code_context[:2000]}"


CODEBASE_TOOLS = [
    codebase_search,
    codebase_list_repos,
    codebase_list_files,
    codebase_show_file,
    codebase_explain_how_to,
]
