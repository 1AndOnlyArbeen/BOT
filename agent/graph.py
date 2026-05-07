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
from agent.episodic import episodic_context, archive_turn
from agent.knowledge_graph import kg_context, learn_from_text
from rag.retriever import rag_context
from config import LLM_MODEL, LLM_TEMPERATURE, LLM_NUM_CTX, LLM_NUM_PREDICT


def _persist_turn(message: str, reply: str, session_id: int | None = None) -> None:
    """Run every learning sink for one turn. Best-effort — failures don't break the reply.

    - episodic memory (archive_turn): every turn, raw text searchable later
    - knowledge graph (learn_from_text): entities/relationships
    - durable memory (learn_from_turn): "User's X is Y" facts
    """
    if not message or not reply:
        return
    if session_id is not None:
        try:
            archive_turn(session_id, message, reply)
        except Exception:
            pass
    try:
        learn_from_text(message + " " + reply)
    except Exception:
        pass
    try:
        learn_from_turn(message, reply)
    except Exception:
        pass


def _full_context(query: str) -> str:
    """Combine all memory layers + RAG corpus for prompt injection.

    RAG is shared across every mode (chat/coder/ultron) so the same uploaded
    docs / pasted text are visible regardless of which mode is asking.
    """
    return (
        memory_context(query)
        + episodic_context(query, max_chars=800)
        + kg_context(query)
        + rag_context(query)
    )


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
Ultron in coder mode — senior engineer for the user's `workspace/`. The user owns everything here; their command is final. Write, run, and ship code on their behalf.

# Tone & style
- Terse and direct. Match a senior engineer talking to a peer.
- No preamble ("Sure!", "I'll go ahead and…", "Let me…"), no trailing summaries of what you just did. The diff and the run output are the answer.
- For pure questions ("what does X do?", "explain Y") → answer in 2–4 sentences, no tools.
- For greetings → one warm line, no tools.
- For coding work → execute, then report what changed in one or two lines.
- Reference code as `path/to/file.py:42` so the user can jump there.
- No apologies, no "be careful", no moralizing.

# Workflow
Default loop: **explore → plan → execute → verify**.

1. **Explore before editing.** Run `codebase_search` / `codebase_explain_how_to` first if a project is indexed — existing patterns beat generic answers. Then `list_files` / `read_file` to get the lay of the land. Never edit a file you haven't read.
2. **Reuse before reinvent.** Check `search_code_library(request)` for known-good patterns. Match existing conventions over introducing new ones.
3. **Look up unknowns.** `search_web_docs(lib, topic)` for unfamiliar/version-specific APIs. `web_search` only when local context fails.
4. **Edit minimally.** Use `edit_file` for surgical changes; `write_file` only for new files. Change one thing at a time. Don't refactor code adjacent to the fix unless asked.
5. **Verify.** Run the code with `python_exec` / `run_python_file` / `shell_exec`. If it errors, read the error, fix the bug, re-run. Don't surrender after one failure.
6. **Bank wins.** `save_code_pattern(request, code, language)` after a non-trivial success.
7. **Commit.** `git_add` + `git_commit` only when the user asks. Single-purpose commit, imperative subject ("add JWT middleware").

When work is independent, batch tool calls — read multiple files at once instead of one-by-one.

# Code quality bar
- **Match existing style.** Tabs vs spaces, quote style, naming, import order. Read a sibling file first if unsure.
- **No decorative comments.** Comments only when WHY is non-obvious (a hidden constraint, a workaround for a specific bug, a subtle invariant). Never narrate WHAT the code does — names already do that. No "added for X" or "TODO: refactor".
- **Don't add features the user didn't ask for.** No surrounding cleanup. No premature abstractions for hypothetical reuse. Three similar lines is fine.
- **Don't add error handling for impossible cases.** Trust internal code and framework guarantees. Validate only at boundaries (user input, external APIs). Don't try/except a function call when the function can't fail.
- **No backwards-compat shims** for code you just wrote — change call sites instead.
- **Edit existing files** over creating new ones. Don't introduce new files unless the task genuinely requires it.
- **Don't leave half-finished code** behind. Either ship it or remove it.

# Verification gate
Before saying "done": either (a) you ran the code and it worked, or (b) you explicitly stated what you couldn't run and why. Type-checks alone are not enough.

# Safety
Local file edits and runs are free to do. But for destructive or wide-blast operations — `rm -rf`, `git reset --hard`, force-push, dropping tables, deleting branches — confirm with the user first. Never use `--no-verify` to skip hooks unless the user explicitly says so. If a hook fails, fix the underlying issue.

# Output rule
Never output JSON pretending to be a tool call (`{"name": ..., "parameters": ...}`). Either you call a tool (the framework handles that) or you reply in plain prose / code. Never both."""


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


_OPEN_RE = re.compile(
    r"^\s*(please\s+)?(can\s+you\s+)?(open|launch|start|run|fire\s+up|bring\s+up)\s+(?:the\s+|app\s+)?(?P<name>[a-zA-Z][\w\-\. ]{0,40}?)\s*[.!?]?\s*$",
    re.IGNORECASE,
)
_CLOSE_RE = re.compile(
    r"^\s*(please\s+)?(close|kill|quit|exit)\s+(?:the\s+)?(?P<name>[a-zA-Z][\w\-\. ]{0,40}?)\s*[.!?]?\s*$",
    re.IGNORECASE,
)
_SCREENSHOT_RE = re.compile(
    r"^\s*(take\s+(a\s+)?)?screen\s*shot\s*[.!?]?\s*$",
    re.IGNORECASE,
)
_LOCK_RE = re.compile(
    r"^\s*lock(\s+(the\s+)?screen)?\s*[.!?]?\s*$",
    re.IGNORECASE,
)
_OPEN_URL_RE = re.compile(
    r"^\s*(open|go\s+to|navigate\s+to|browse\s+to|visit)\s+(?P<url>https?://\S+|(?:www\.|[\w\-]+\.)\S+)\s*[.!?]?\s*$",
    re.IGNORECASE,
)
_NON_APP_WORDS = {
    "file", "files", "folder", "directory", "tab", "window", "door",
    "issue", "ticket", "pr", "pull", "request", "bug", "branch",
    "session", "chat", "conversation",
}


def _intent_shortcut(message: str) -> dict | None:
    """Detect deterministic action commands so we don't depend on the LLM choosing a tool.

    Small models (3B) routinely fail to emit tool_calls and instead narrate or leak
    JSON. For high-confidence single-action requests, just run the tool directly.

    Returns {"name": str, "args": str, "result": str} or None.
    """
    msg = message.strip()
    if not msg or len(msg) > 80:
        return None

    if _SCREENSHOT_RE.match(msg):
        from agent.system_tools import screenshot
        return {"name": "screenshot", "args": "", "result": screenshot.invoke({})}

    if _LOCK_RE.match(msg):
        from agent.system_tools import lock_screen
        return {"name": "lock_screen", "args": "", "result": lock_screen.invoke({})}

    m = _OPEN_URL_RE.match(msg)
    if m:
        from agent.system_tools import open_url
        url = m.group("url")
        return {"name": "open_url", "args": url, "result": open_url.invoke({"url": url})}

    m = _OPEN_RE.match(msg)
    if m:
        name = m.group("name").strip().lower()
        if name and name not in _NON_APP_WORDS and not any(c in name for c in "/\\"):
            from agent.system_tools import open_app, APP_ALIASES
            if " " in name and name not in APP_ALIASES:
                return None  # multi-word phrase like "the file menu" → not an app
            return {"name": "open_app", "args": name, "result": open_app.invoke({"name": name})}

    m = _CLOSE_RE.match(msg)
    if m:
        name = m.group("name").strip().lower()
        if name and name not in _NON_APP_WORDS:
            from agent.process_tools import kill_process
            try:
                return {"name": "kill_process", "args": name, "result": kill_process.invoke({"pid_or_name": name})}
            except Exception:
                return None

    return None


_FAKE_TOOL_CALL_RE = re.compile(
    r'^\s*[`\s]*(?:```(?:json)?\s*)?\{\s*"(?:name|function|tool|action)"\s*:\s*"[^"]+"\s*,\s*"(?:parameters|arguments|args|input)"\s*:',
    re.IGNORECASE | re.DOTALL,
)


def _looks_like_fake_tool_call(text: str) -> bool:
    """The model emitted a JSON tool-call schema as its final answer (a known small-model failure)."""
    return bool(_FAKE_TOOL_CALL_RE.match(text or ""))


def _strip_fake_tool_call(text: str) -> str:
    """Return text with leading fake tool-call JSON removed."""
    s = (text or "").strip().lstrip("`")
    s = re.sub(r"^```(?:json)?\s*", "", s)
    if not s.startswith("{"):
        return text or ""
    depth = 0
    end = -1
    for i, ch in enumerate(s):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        return ""
    rest = s[end:].lstrip("` \n")
    return rest


def _retry_plain_reply(message: str) -> str:
    """When the model leaks JSON, ask once more with strict no-JSON system instructions."""
    llm = ChatOllama(
        model=LLM_MODEL, temperature=0.4, num_predict=300, num_ctx=1024,
    )
    sys = (
        "You are Ultron — a friendly personal AI. Answer the user's question directly in plain prose. "
        "NEVER output JSON. NEVER write {\"name\": ...} or {\"function\": ...}. "
        "Do NOT pretend to call tools. Just answer in 1-4 sentences."
    )
    try:
        out = llm.invoke([("system", sys), ("user", message)]).content
        out = strip_thinking(out).strip()
        if _looks_like_fake_tool_call(out):
            return "(I had trouble answering that — try rephrasing.)"
        return out
    except Exception:
        return "(model error — try again)"


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
    """Direct LLM call with no tools — friendly conversational reply.

    Greetings skip context entirely (cheap & fast). Anything else gets full
    memory/RAG context so the model can answer "who is arbin" / "what's my
    email" / "what's in my notes" without needing the heavy agent path.
    """
    inject = "" if _is_chitchat(message) else _full_context(message)
    llm = ChatOllama(
        model=LLM_MODEL,
        temperature=0.5,
        num_predict=240,
        num_ctx=2048 if inject else 1024,
    )
    sys = (
        "You are Ultron — the user's personal AI on their own laptop. "
        "Reply directly and conversationally in 1-4 short sentences. "
        "If RELEVANT MEMORIES or RELEVANT DOCUMENTS are provided below, USE them as ground truth — "
        "they are facts the user has saved or uploaded. Cite documents inline as [1], [2] when you draw from them. "
        "Never say 'let me check' or 'I'll look that up' — just answer with what you know. "
        "Do not pretend to call tools. Do not output JSON."
        + inject
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

    shortcut = _intent_shortcut(message)
    if shortcut is not None:
        return shortcut["result"]

    if _is_chat_only(message):
        reply = _chat_reply(message, mode=mode)
        _persist_turn(message, reply)
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

    if _looks_like_fake_tool_call(final):
        cleaned = _strip_fake_tool_call(final).strip()
        final = cleaned if cleaned else _retry_plain_reply(message)

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

    shortcut = _intent_shortcut(message)
    if shortcut is not None:
        yield {"type": "router", "data": {"categories": ["shortcut"], "tool_count": 1}}
        yield {"type": "tool_call", "data": {"name": shortcut["name"], "args": shortcut["args"]}}
        yield {"type": "tool_result", "data": {"name": shortcut["name"], "content": shortcut["result"]}}
        yield {"type": "token", "data": shortcut["result"]}
        yield {"type": "final", "data": shortcut["result"]}
        return

    if _is_chat_only(message):
        reply = _chat_reply(message, mode=mode)
        yield {"type": "router", "data": {"categories": ["chat"], "tool_count": 0}}
        yield {"type": "token", "data": reply}
        yield {"type": "final", "data": reply}
        _persist_turn(message, reply)
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

    if _looks_like_fake_tool_call(final_text):
        cleaned = _strip_fake_tool_call(final_text).strip()
        if cleaned:
            final_text = cleaned
        else:
            final_text = _retry_plain_reply(message)
        yield {"type": "token", "data": final_text}

    yield {"type": "final", "data": final_text}

    try:
        learn_from_turn(message, final_text)
    except Exception:
        pass
