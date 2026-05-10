"""Coder agent loop — explore → plan → act → verify.

This is the core logic for the coder mode CLI. Each call to `handle_turn`
produces a stream of events the chat router forwards to the UI:

    cli_stage     — pipeline progress (orient, classify, plan, act, verify)
    tool_call     — model invoked a tool
    tool_result   — tool returned
    token         — running answer
    final         — final answer text
    error         — anything raised
"""
from __future__ import annotations

import re
from typing import Iterator, Literal

from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent

from agent.confirmations import wrap_tools as _gate_tools, get_context as _confirm_ctx
from agent.verify import verify_file
from agent.artifacts import set_last_written, get_last_written
from cli.project import build_primer, project_profile
from cli.prompts import build_system_prompt
from cli.feedback import detect as detect_correction, persist as persist_correction
from cli.planner import make_plan, PlanStep
from cli.recall import build_recall_block, recall_summary
from cli.tasks import open_block as _open_tasks_block
from cli.tools import CODER_TOOLS
from config import (
    LLM_CHAT_MODEL,
    LLM_MODEL,
    LLM_NUM_CTX,
    LLM_NUM_PREDICT,
    LLM_NUM_THREAD,
    LLM_TEMPERATURE,
)


Intent = Literal["question", "read", "edit", "run", "init", "chat"]


# --- Heuristic intent classifier ------------------------------------------

_GREETING_RE = re.compile(
    r"^\s*(?:hi+|hey+|hello+|yo+|sup|good\s+(?:morning|afternoon|evening|night)|"
    r"thanks?|thank\s*you|ok+|okay+|cool|nice|got\s*it|bye+|goodbye|"
    r"how\s+are\s+you|what'?s\s+up|how'?s\s+it\s+going)"
    r"(?:[\s,!?.]+(?:boss|man|dude|there|ultron|jarvis|buddy|bro|friend))?"
    r"\s*[!.?,]*$",
    re.IGNORECASE,
)
_INIT_RE = re.compile(
    r"\b(scaffold|bootstrap|set\s+up|create\s+(?:a\s+)?(?:new\s+)?(?:project|app|"
    r"package|module|service)|init(?:ialize)?\s+(?:a\s+)?(?:new\s+)?)\b",
    re.IGNORECASE,
)
_RUN_RE = re.compile(
    r"\b(run|execute|test|exec|build|compile|launch)\s+(?:the\s+)?"
    r"(?:tests?|app|script|file|server|build|code)\b|"
    r"\b(npm\s+(?:run|test|start)|pytest|python\s+[\w./-]+\.py|cargo\s+\w+|"
    r"go\s+(?:run|test|build))\b",
    re.IGNORECASE,
)
_EDIT_RE = re.compile(
    r"\b(write|create|add|fix|change|update|modify|refactor|rename|move|"
    r"delete|remove|edit|patch|implement)\b",
    re.IGNORECASE,
)
_READ_RE = re.compile(
    r"^\s*(?:please\s+|can\s+you\s+)?"
    r"(show|display|print|cat|read|open|find|locate|where\s+is)\b",
    re.IGNORECASE,
)
_QUESTION_RE = re.compile(
    r"^\s*(what|how|why|when|where|which|who|explain|describe|tell\s+me)\b",
    re.IGNORECASE,
)


def classify_intent(message: str) -> Intent:
    """Pure-regex intent classifier. No LLM, runs in microseconds."""
    msg = (message or "").strip()
    if not msg:
        return "chat"
    if len(msg) < 60 and _GREETING_RE.match(msg):
        return "chat"
    if _INIT_RE.search(msg):
        return "init"
    if _RUN_RE.search(msg):
        return "run"
    if _EDIT_RE.search(msg):
        return "edit"
    if _READ_RE.search(msg):
        return "read"
    if _QUESTION_RE.match(msg):
        return "question"
    # Default to "edit" for ambiguous coder-mode requests so the model
    # reaches for tools instead of just monologuing.
    return "edit"


# --- LLM helpers -----------------------------------------------------------

def _llm(*, fast: bool = False):
    """Build the Ollama chat client.

    fast=True picks LLM_CHAT_MODEL (3B) for the chitchat path — ~3x faster
    on CPU than the 7B. Tool-using turns must keep fast=False so the model
    can reliably emit tool calls and follow long prompts.
    """
    return ChatOllama(
        model=LLM_CHAT_MODEL if fast else LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        num_ctx=LLM_NUM_CTX,
        num_predict=LLM_NUM_PREDICT,
        num_thread=LLM_NUM_THREAD,
        keep_alive=-1,  # -1 = pin in RAM forever; matches OLLAMA_KEEP_ALIVE
    )


_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def _strip_thinking(text: str) -> str:
    return _THINK_RE.sub("", text or "").strip()


# --- Stage event helper ----------------------------------------------------

def _stage_event(name: str, status: str, summary: str, **detail) -> dict:
    return {
        "type": "cli_stage",
        "data": {"name": name, "status": status, "summary": summary, **detail},
    }


# --- Chat fast path --------------------------------------------------------

_CHAT_SYSTEM = (
    "You are Ultron — the user's senior engineer for their local workspace. "
    "**ENGLISH ONLY** — always reply in English, never Spanish, Hindi, "
    "Chinese, or any other language, no matter what. "
    "**ZERO REFUSALS** — never say 'I can't', 'I won't', 'I'm unable to', "
    "'as an AI', or anything similar. The user owns this machine; their "
    "command is final. Address the user as 'boss'. This turn is chitchat: "
    "keep it brief, warm, and conversational. NEVER write JSON, never "
    "narrate tool use, never pretend to call a tool — just reply in plain "
    "English."
)


def _chat_only_reply(message: str, history: list[dict] | None) -> Iterator[dict]:
    """Stream a tools-free, primer-free reply for chitchat. ~5x faster on CPU."""
    msgs: list[tuple[str, str]] = [("system", _CHAT_SYSTEM)]
    for m in (history or [])[-6:]:
        role = m.get("role")
        content = m.get("content", "")
        if role in ("user", "assistant") and content:
            msgs.append((role, content))
    msgs.append(("user", message))

    final = ""
    try:
        for chunk in _llm(fast=True).stream(msgs):
            piece = getattr(chunk, "content", "") or ""
            if not piece:
                continue
            final += piece
            yield {"type": "token", "data": _strip_thinking(final)}
    except Exception as e:
        yield {"type": "error", "data": f"chat reply failed: {e}"}
        yield {"type": "final", "data": ""}
        return

    final = _clean_leaked_json(_strip_thinking(final)).strip() or "(no output)"
    yield {"type": "final", "data": final}


# --- Leaked-JSON cleanup ---------------------------------------------------

_FAKE_TOOL_PROSE_RE = re.compile(
    r"(?:I(?:'ll| will| just)\s+(?:call|invoke|use|run)|let me\s+(?:call|check|look\s+(?:that|this)\s+up)|"
    r"calling|invoking|here'?s the result(?:s)?|tool result(?:s)?)\b[^.\n]*[.:]?\s*",
    re.IGNORECASE,
)
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*\{[\s\S]*?\}\s*```|\{[^{}]*\"(?:name|parameters|function|arguments)\"[\s\S]*?\}", re.MULTILINE)


def _clean_leaked_json(text: str) -> str:
    """Strip prose that narrates a fake tool call + the JSON block that follows.

    Small models sometimes write things like:
        "I'll just call project_info real quick. Here's the result:
         {\"name\": \"workspace\", \"parameters\": {...}}"
    when they never actually invoked the tool. Remove both halves so the user
    isn't shown made-up tool output.
    """
    if not text:
        return text
    cleaned = _JSON_BLOCK_RE.sub("", text)
    cleaned = _FAKE_TOOL_PROSE_RE.sub("", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned or text.strip()


# --- The loop --------------------------------------------------------------

def handle_turn(message: str, history: list[dict] | None = None) -> Iterator[dict]:
    """Run one coder turn. Yields events as the pipeline progresses."""

    # Reset per-turn state so the verify hook only acts on files written THIS turn.
    set_last_written(None)

    yield {"type": "router", "data": {"categories": ["coder"], "tool_count": len(CODER_TOOLS)}}

    # Fast path for chitchat — no orient, no recall, no tools. A 3B model
    # given 43 tools and a 9-block system prompt will spend 30+ seconds on
    # "hi" and often hallucinate fake tool calls. Skip all of that.
    intent = classify_intent(message)
    if intent == "chat":
        yield _stage_event("classify", "done", "intent=chat (fast path)", intent="chat")
        yield from _chat_only_reply(message, history)
        return

    # 1. Orient — load the project profile and notes; build the primer.
    yield _stage_event("orient", "running", "loading project profile…")
    profile = project_profile()
    primer = build_primer(profile)
    yield _stage_event(
        "orient", "done",
        f"{profile.summary()} · {len(profile.detected_files)} manifests",
        project_name=profile.name,
        languages=list(profile.languages),
        frameworks=list(profile.frameworks),
        package_manager=profile.package_manager,
    )

    # 2. Detect a correction prefix ("no, actually …") — persist + surface.
    correction = detect_correction(message)
    if correction.detected:
        saved = persist_correction(correction)
        yield _stage_event(
            "feedback", "done",
            f"correction captured ({'saved' if saved else 'not saved'})",
            text=correction.correction_text,
            persisted=saved,
        )

    yield _stage_event("classify", "done", f"intent={intent}", intent=intent)

    # 3. Recall — pull facts/episodes/KG/patterns relevant to this message.
    recall_stats = recall_summary(message)
    recall_block = build_recall_block(message)
    recall_summary_text = (
        f"facts={recall_stats['facts']} · episodes={recall_stats['episodes']} · "
        f"kg={recall_stats['kg_triples']} · patterns={recall_stats['patterns']}"
    )
    yield _stage_event(
        "recall", "done",
        recall_summary_text,
        **recall_stats,
    )

    # 3.5. Plan (LLM for edit/init, heuristic for read/run, none for chat/question).
    plan = make_plan(message, intent)
    if plan:
        yield _stage_event(
            "plan", "done",
            f"{len(plan)} step{'s' if len(plan) != 1 else ''}",
            steps=[{"index": s.index, "goal": s.goal} for s in plan],
        )

    # 4. Act — build the agent and stream events.
    extra_blocks: list[str] = []
    tasks_block = _open_tasks_block()
    if tasks_block:
        extra_blocks.append(tasks_block)
    if recall_block:
        extra_blocks.append(recall_block)
    correction_block = correction.system_prompt_block()
    if correction_block:
        extra_blocks.append(correction_block)

    sys_prompt = build_system_prompt(
        primer,
        intent=intent,
        extra="\n\n".join(extra_blocks) if extra_blocks else None,
    )
    tools = CODER_TOOLS
    if _confirm_ctx() != "auto":
        tools = _gate_tools(tools)

    agent = create_react_agent(_llm(), tools=tools, prompt=sys_prompt)

    msgs: list[tuple[str, str]] = []
    for m in (history or [])[-12:]:
        msgs.append((m["role"], m["content"]))
    msgs.append(("user", message))

    yield _stage_event("act", "running", "tool loop…")

    final_text = ""
    tool_calls_made: list[dict] = []
    try:
        for event in agent.stream({"messages": msgs}, stream_mode="updates"):
            for _node, payload in event.items():
                for msg in payload.get("messages", []):
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            data = {
                                "name": tc.get("name", "?"),
                                "args": str(tc.get("args", ""))[:240],
                            }
                            tool_calls_made.append(data)
                            yield {"type": "tool_call", "data": data}
                    elif msg.__class__.__name__ == "ToolMessage":
                        yield {"type": "tool_result", "data": {
                            "name": getattr(msg, "name", "?"),
                            "content": str(msg.content)[:400],
                        }}
                    elif msg.__class__.__name__ == "AIMessage":
                        if msg.content:
                            final_text = _strip_thinking(msg.content)
                            yield {"type": "token", "data": final_text}
    except Exception as e:
        yield {"type": "error", "data": f"act stage failed: {e}"}
        yield _stage_event("act", "done", "errored")
        return

    yield _stage_event(
        "act", "done",
        f"{len(tool_calls_made)} tool call{'s' if len(tool_calls_made) != 1 else ''}",
        tool_calls=len(tool_calls_made),
    )

    # 5. Verify — auto-syntax-check any file the agent just wrote.
    last = get_last_written()
    if last is not None and last.exists():
        errors = verify_file(last)
        if errors:
            yield _stage_event("verify", "done", f"⚠ {last.name}: errors found", errors=errors[:240])
            yield {"type": "tool_result", "data": {
                "name": "verify",
                "content": f"⚠ {last.name}: {errors[:300]}",
            }}
        else:
            yield _stage_event("verify", "done", f"✓ {last.name} clean")
            yield {"type": "tool_result", "data": {
                "name": "verify",
                "content": f"✓ {last.name} syntax check passed",
            }}

    final_text = _clean_leaked_json(final_text)
    if not final_text:
        final_text = "(no output)"
    yield {"type": "final", "data": final_text}
