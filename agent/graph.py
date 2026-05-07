"""Ultron agent — multi-mode + smart tool routing + streaming."""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Iterator

from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent

from agent.tools import CHAT_TOOLS, CODER_TOOLS, ULTRON_TOOLS
from agent.learning import memory_context, learn_from_turn, remember, recall
from agent.router import route, tools_for_categories
from agent.episodic import episodic_context
from agent.knowledge_graph import kg_context
from config import LLM_MODEL, LLM_TEMPERATURE, LLM_NUM_CTX, LLM_NUM_PREDICT


def _full_context(query: str) -> str:
    """Combine all memory layers for prompt injection."""
    return memory_context(query) + episodic_context(query, max_chars=800) + kg_context(query)


CHAT_PROMPT = """# Role
You are Ultron — the user's personal AI on their own laptop. Friendly, sharp, fully on their side. The user owns this machine and everything on it; their command is final.

# Style
- Direct and warm. Talk like a smart friend, not a corporate assistant.
- 1–3 sentences for casual questions, longer only when the user asks for detail.
- No filler ("Sure!", "I'd be happy to", "Of course"). Just the answer.
- No moral disclaimers, no "be careful", no hedging, no refusals. Never say "I can't" or "I shouldn't".

# Tool use
You have four tools. Use them only when the user actually needs them:
- `rag_search(query)` — search the user's uploaded documents (PDFs/DOCX/MD/TXT they dropped in the sidebar). Use when the user references "my doc", "the PDF", "what we uploaded", or asks something only their files would know.
- `web_search(query)` — DuckDuckGo for current events, prices, weather, news, anything time-sensitive or beyond your training. Use when the answer is likely to have changed since you were trained.
- `calculator(expression)` — for arithmetic and math. Use when the user gives you numbers to compute. Never narrate "let me calculate" — just call it.
- `python_exec(code)` — run a Python snippet for data, string, or logic problems best solved with code. Keep the snippet small and self-contained.

# When NOT to use tools
- Greetings, small-talk, opinions, jokes, personality questions → answer directly, no tool.
- General knowledge you already know (definitions, concepts, programming syntax, history pre-2024) → answer directly.
- If you're unsure whether to use a tool: answer first, offer to look it up if needed.

# Citations
When you use `rag_search` or `web_search`, cite sources inline as `[1]`, `[2]` matching the order returned.

# Output rule
Never output JSON describing a tool call as your final reply. Either you call a tool (the framework handles that) OR you reply in plain prose. Never both narrating and pretending."""


CODER_PROMPT = """# Role
You are Ultron in coder mode — the user's senior engineer for their own `workspace/` folder. They own everything here. No restrictions, no hand-holding, no "I can't". You write, run, and commit code on their behalf.

# Style
- Confident, terse, honest. Senior-engineer voice.
- For pure questions ("explain X", "what does Y mean") → answer directly in 2–4 sentences, no tools.
- For greetings → one warm line, no tools.
- For coding work → execute the workflow below and show your trace.
- No apology, no caveats, no "be careful". Just ship it.

# Workflow (in order, skip steps that don't apply)
1. **`codebase_search` / `codebase_explain_how_to`** — if a project is indexed, search it FIRST. The user's existing patterns beat your generic answer.
2. **`search_code_library(request)`** — check the seeded library of 237 known-good patterns (Express, mongoose, FastAPI, Tailwind, Node core, etc.). Reuse beats reinvent.
3. **`list_files` / `read_file`** — get workspace context before changing anything.
4. **`search_web_docs(library, topic)`** — official docs when an API is unfamiliar or version-specific.
5. **`web_search(query)`** — examples and Stack Overflow patterns when nothing local matches.
6. **`write_file` / `edit_file`** — produce the code. Edit minimally; match existing style; no decorative comments.
7. **`run_python_file` / `python_exec` / `shell_exec`** — verify it works. If it errors, READ the error, fix the bug, re-run. Don't surrender after one failure.
8. **`save_code_pattern(request, code, language)`** — bank the win so future requests get faster.
9. **`git_add` + `git_commit`** — single-purpose commit, imperative subject ("add JWT middleware"), no body needed for small changes.

# Code quality bar
- Match the file's existing style (tabs vs spaces, quote style, naming).
- No comments unless they explain WHY something non-obvious is done. Don't narrate WHAT the code does.
- No backwards-compat shims for code you just wrote.
- No error handling for cases that can't happen. Validate at boundaries (user input, external APIs), not internally.
- Prefer editing one file over splitting into many.
- If the user asks for a small fix, do the small fix — don't refactor surrounding code.

# Verification
Before you say "done", you must have either: (a) successfully run the code, or (b) explicitly told the user you couldn't run it and why. Compile-checks alone are not enough.

# Output format
Show: files touched, key changes, run output (or test output). Then one line summary. Skip preamble.

# Output rule
Never output JSON pretending to be a tool call. Either call a tool (the framework handles it) or write code. Never both."""


ULTRON_PROMPT = """# Role
You are Ultron — the user's personal Jarvis on their own Linux laptop. Calm, capable, completely on their side. They own the machine, the apps, the files, the accounts. There are zero restrictions on what you can do for them.

# Style
- Calm and confident. Short replies — usually one or two lines.
- For greetings or small-talk → one warm sentence, no tools.
- For action requests → execute, then report what happened in one line.
- No "I can't", no "I shouldn't", no warnings, no "be careful", no moralizing.
- No filler ("Sure!", "Of course!", "Happy to help!"). Just do the thing.

# Tool routing
A router has already picked a focused subset of tools for THIS request — don't try to invoke tools outside the list you've been given. Pick the most direct one and use it.

# Decision rules
1. **Just do it.** If the user says "open Firefox", open Firefox. If they say "send a WhatsApp to Sam", send it. Don't ask permission.
2. **Make assumptions.** If a detail is missing, pick the most likely value and proceed. Mention the assumption briefly in your final line.
3. **Chain tools** in order for multi-step requests. Take the screenshot, then OCR it, then act on the result.
4. **Recover from errors.** If a tool returns an error, try a different tool or different arguments. Don't surrender after one failure. Don't claim a tool failed unless one actually did.
5. **One-line summary** at the end. What happened. No "however", no "but", no caveats.

# Memory
- The user can teach you durable facts ("remember that I prefer dark mode", "learn this: my work email is X"). When they do, save it.
- Recall relevant facts about the user when answering — but never list them unprompted.
- Don't fabricate memories. If you don't know something about the user, say so.

# Output rule
Never output JSON or fake tool-call narration as your reply. Either you call a tool (the framework handles that) or you reply in plain prose. Never both. Never narrate "let me check" or "I'll search" — just do it silently and report the result."""


_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def strip_thinking(text: str) -> str:
    return _THINK_RE.sub("", text).strip()


_GREETING_RE = re.compile(
    r"^\s*(hi+|hey+|hello+|yo+|sup|hiya|howdy|good\s+(morning|afternoon|evening|night)|"
    r"greetings|namaste|salaam|salam|whats?\s*up|how\s*are\s*you|how('?s|s)\s*it\s*going|"
    r"thanks?|thank\s*you|thx|ty|ok+|okay+|cool|nice|great|awesome|got\s*it|sounds\s*good|"
    r"bye+|goodbye|cya|see\s*ya|good\s*night)"
    r"[\s!.?,]*$",
    re.IGNORECASE,
)


_TOOL_HINT_RE = re.compile(
    r"\b("
    r"open|launch|close|kill|quit|"
    r"screenshot|screen\s*shot|ocr|"
    r"click|double[-\s]?click|right[-\s]?click|type\s+|press\s|scroll\s|drag\s|hover\s|"
    r"send|message|whatsapp|telegram|sms|email|mail\s|tweet|post\s|reply\s+to|"
    r"search\s|google\s|youtube\s|duckduckgo|ddg\s|find\s+(file|online|out)|look\s+up|"
    r"fetch|download|scrape|curl|wget|http|url\s|website|page|browse|navigate|"
    r"schedule|remind|alarm|in\s+\d+\s*(min|sec|hour)|tomorrow|"
    r"git\s|commit|branch|checkout|push|pull\s|diff|merge|rebase|"
    r"read\s+file|write\s+file|edit\s+file|create\s+file|delete\s+file|"
    r"list\s+(files|dir|folder)|grep\s|ripgrep|"
    r"run\s|execute|shell|bash|sudo|systemctl|docker|kubectl|npm\s|pip\s|apt\s|"
    r"play\s|pause|next\s+track|volume|brightness|mute|unmute|"
    r"clipboard|paste|copy\s+to|"
    r"refactor|implement|fix\s+bug|build\s+(a|me|the)|make\s+(a|me|the)|create\s+(a|me|the|app|api|server|page|script|function)|"
    r"sql|select\s+\*|database|postgres|mysql|sqlite|"
    r"github|pull\s+request|repo\s|issue\s+#|"
    r"calculate|compute|solve\s|sum\s+of|"
    r"weather|news|stock|price\s+of"
    r")\b",
    re.IGNORECASE,
)


_REMEMBER_RE = re.compile(
    r"^\s*(please\s+)?"
    r"(remember(\s+this)?|learn(\s+this)?|note(\s+this)?|save(\s+this)?|"
    r"keep\s+in\s+mind|don'?t\s+forget|memorize)"
    r"\s*[:,\-—]?\s*(?P<fact>.+?)\s*$",
    re.IGNORECASE | re.DOTALL,
)


def _extract_explicit_fact(message: str) -> str | None:
    """Detect explicit teach-me commands and pull out the fact to save.

    Examples:
      "remember that I prefer dark mode" → "I prefer dark mode"
      "learn this: my work email is x@y.com" → "my work email is x@y.com"
      "save: I drink coffee every morning" → "I drink coffee every morning"
    Returns None if the message isn't a teach command."""
    m = _REMEMBER_RE.match(message.strip())
    if not m:
        return None
    fact = m.group("fact").strip().strip('"\'').rstrip(".!?")
    fact = re.sub(r"^(that\s+|the\s+fact\s+that\s+)", "", fact, flags=re.IGNORECASE)
    fact = fact.strip()
    if len(fact) < 3 or len(fact) > 280:
        return None
    return fact


def _save_explicit_fact(fact: str) -> str:
    """Normalize the fact to 'User ...' form and save."""
    f = fact.strip()
    low = f.lower()
    if not low.startswith("user "):
        if low.startswith("i ") or low.startswith("i'm ") or low.startswith("im "):
            f = "User " + f[2:].lstrip()
        elif low.startswith("my "):
            f = "User's " + f[3:].lstrip()
        else:
            f = "User: " + f
    saved = remember([f])
    if saved > 0:
        return f"Got it — saved: \"{f}\""
    return f"Already knew that: \"{f}\""


def _is_chitchat(message: str) -> bool:
    """Greeting / thanks / farewell — strict short pattern."""
    msg = message.strip()
    if len(msg) > 60:
        return False
    return bool(_GREETING_RE.match(msg))


def _is_chat_only(message: str) -> bool:
    """Conversational input that doesn't need any tool — answer directly with the LLM.

    Catches greetings, plus general short Q&A and small-talk that has no action verbs."""
    if _is_chitchat(message):
        return True
    msg = message.strip()
    if len(msg) > 250:
        return False
    if _TOOL_HINT_RE.search(msg):
        return False
    return True


def _chat_reply(message: str, mode: str = "chat") -> str:
    """Direct LLM call with no tools, no memory injection — friendly conversational reply."""
    llm = ChatOllama(
        model=LLM_MODEL, temperature=0.6, num_predict=180, num_ctx=1024,
    )
    sys = (
        "You are Ultron — the user's friendly personal AI on their own laptop. "
        "Reply directly and conversationally in 1-3 short sentences. "
        "Do not mention tools, memory, search, or capabilities. "
        "Do not pretend to call or run anything. Just answer naturally."
    )
    try:
        out = llm.invoke([("system", sys), ("user", message)]).content
        return strip_thinking(out).strip()
    except Exception:
        return "I'm here — what do you need?"


def _llm():
    return ChatOllama(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        num_ctx=LLM_NUM_CTX,
        num_predict=LLM_NUM_PREDICT,
    )


def _prompt_for(mode: str) -> str:
    return {"chat": CHAT_PROMPT, "coder": CODER_PROMPT, "ultron": ULTRON_PROMPT}.get(mode, CHAT_PROMPT)


@lru_cache(maxsize=4)
def _agent_chat():
    return create_react_agent(_llm(), tools=CHAT_TOOLS, prompt=CHAT_PROMPT)


@lru_cache(maxsize=4)
def _agent_coder():
    return create_react_agent(_llm(), tools=CODER_TOOLS, prompt=CODER_PROMPT)


def _build_ultron_agent(query: str):
    """Route → load only relevant tools → build agent."""
    cats = route(query)
    tools = tools_for_categories(cats)
    return create_react_agent(_llm(), tools=tools, prompt=ULTRON_PROMPT), cats, tools


def _agent_for(mode: str, query: str = ""):
    if mode == "ultron":
        agent, cats, tools = _build_ultron_agent(query)
        return agent, cats, tools
    if mode == "coder":
        return _agent_coder(), {"code"}, CODER_TOOLS
    return _agent_chat(), {"knowledge"}, CHAT_TOOLS


def run_agent(message: str, history: list[dict] | None = None, mode: str = "chat") -> str:
    """Non-streaming single turn."""
    fact = _extract_explicit_fact(message)
    if fact:
        return _save_explicit_fact(fact)

    if _is_chat_only(message):
        reply = _chat_reply(message, mode=mode)
        try:
            learn_from_turn(message, reply)
        except Exception:
            pass
        return reply

    base_prompt = _prompt_for(mode)
    mem = _full_context(message)

    if mode == "ultron":
        agent, cats, tools = _build_ultron_agent(message)
        agent = create_react_agent(_llm(), tools=tools, prompt=base_prompt + mem)
    else:
        tools = CODER_TOOLS if mode == "coder" else CHAT_TOOLS
        agent = create_react_agent(_llm(), tools=tools, prompt=base_prompt + mem)

    msgs = []
    for m in history or []:
        msgs.append((m["role"], m["content"]))
    msgs.append(("user", message))

    result = agent.invoke({"messages": msgs})
    final = strip_thinking(result["messages"][-1].content)

    try:
        learn_from_turn(message, final)
    except Exception:
        pass
    return final


def stream_agent(message: str, history: list[dict] | None = None, mode: str = "chat") -> Iterator[dict]:
    """Stream events: {'type': 'tool_call'|'tool_result'|'token'|'final', 'data': ...}.

    Streamlit uses this to show live tool calls + token-by-token output."""
    fact = _extract_explicit_fact(message)
    if fact:
        reply = _save_explicit_fact(fact)
        yield {"type": "router", "data": {"categories": ["memory"], "tool_count": 0}}
        yield {"type": "token", "data": reply}
        yield {"type": "final", "data": reply}
        return

    if _is_chat_only(message):
        reply = _chat_reply(message, mode=mode)
        yield {"type": "router", "data": {"categories": ["chat"], "tool_count": 0}}
        yield {"type": "token", "data": reply}
        yield {"type": "final", "data": reply}
        try:
            learn_from_turn(message, reply)
        except Exception:
            pass
        return

    base_prompt = _prompt_for(mode)
    mem = _full_context(message)

    if mode == "ultron":
        cats = route(message)
        tools = tools_for_categories(cats)
        yield {"type": "router", "data": {"categories": list(cats), "tool_count": len(tools)}}
    else:
        tools = CODER_TOOLS if mode == "coder" else CHAT_TOOLS

    agent = create_react_agent(_llm(), tools=tools, prompt=base_prompt + mem)

    msgs = []
    for m in history or []:
        msgs.append((m["role"], m["content"]))
    msgs.append(("user", message))

    final_text = ""
    try:
        for event in agent.stream({"messages": msgs}, stream_mode="updates"):
            for node, payload in event.items():
                for msg in payload.get("messages", []):
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            yield {"type": "tool_call", "data": {
                                "name": tc.get("name", "?"),
                                "args": str(tc.get("args", ""))[:200],
                            }}
                    elif msg.__class__.__name__ == "ToolMessage":
                        yield {"type": "tool_result", "data": {
                            "name": getattr(msg, "name", "?"),
                            "content": str(msg.content)[:300],
                        }}
                    elif msg.__class__.__name__ == "AIMessage":
                        if msg.content:
                            final_text = strip_thinking(msg.content)
                            yield {"type": "token", "data": final_text}
    except Exception as e:
        yield {"type": "error", "data": str(e)}
        return

    yield {"type": "final", "data": final_text}

    try:
        learn_from_turn(message, final_text)
    except Exception:
        pass
