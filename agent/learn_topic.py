"""Learn-on-demand: Ultron researches a new topic, then files patterns into the library."""
from __future__ import annotations

import re

from langchain_core.tools import tool
from langchain_ollama import ChatOllama

from agent.code_library import save_pattern
from agent.web_tools import fetch_url
from config import LLM_MODEL


_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)


def _llm():
    return ChatOllama(model=LLM_MODEL, temperature=0.1, num_predict=900)


SYNTH_PROMPT = """You are reading official documentation. Extract 3-5 minimal, idiomatic CODE PATTERNS from the doc text.

Each pattern MUST have:
- request: a natural-language ask (e.g. "create a basic Flask app")
- code: the runnable code (no commentary, no markdown fences)
- language: file ext or language name

Return JSON only:
{{"patterns": [{{"request":"...","code":"...","language":"..."}}, ...]}}

Topic: {topic}
Documentation:
{docs}

JSON:"""


def _parse(raw: str) -> list[dict]:
    import json
    text = _THINK.sub("", raw).strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    out = []
    for p in data.get("patterns", [])[:8]:
        if isinstance(p, dict) and p.get("request") and p.get("code"):
            out.append({
                "request": p["request"][:300],
                "code": p["code"][:4000],
                "language": p.get("language", "text"),
            })
    return out


@tool
def learn_topic(topic: str, doc_url: str = "") -> str:
    """Research a new topic, save patterns to memory.
    topic: 'flask', 'astro', 'svelte', 'graphql', 'next.js routing', etc.
    doc_url: optional — pass an official docs URL. If empty, fetches via web search.

    After this runs, future 'how do I X with <topic>?' questions will hit the library."""
    docs = ""
    if doc_url:
        docs = fetch_url.invoke({"url": doc_url})
    else:
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                hits = list(ddgs.text(f"{topic} official documentation getting started", max_results=3))
            if hits:
                top = hits[0]["href"]
                docs = fetch_url.invoke({"url": top})
        except Exception as e:
            return f"[error] couldn't search: {e}"

    if not docs or docs.startswith("[error]"):
        return f"[error] couldn't fetch docs: {docs[:200]}"

    docs = docs[:6000]
    try:
        resp = _llm().invoke(SYNTH_PROMPT.format(topic=topic, docs=docs)).content
    except Exception as e:
        return f"[error] synth failed: {e}"

    patterns = _parse(resp)
    if not patterns:
        return f"[warn] no clean patterns extracted for '{topic}'. Raw: {resp[:200]}"

    saved = 0
    for p in patterns:
        save_pattern(
            request=p["request"],
            code=p["code"],
            language=p["language"],
            notes=f"learned from {topic}",
            success=True,
        )
        saved += 1
    return f"✓ learned '{topic}' — saved {saved} patterns to the code library."


LEARN_TOPIC_TOOLS = [learn_topic]
