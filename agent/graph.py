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
from agent.confirmations import wrap_tools as _gate_tools, get_context as _confirm_ctx
from agent.episodic import episodic_context, archive_turn
from agent.knowledge_graph import kg_context, learn_from_text
from agent.grounding import (
    is_self_referential, lookup_self_facts, refusal_for_self_question,
    is_code_in_chat_failure,
)
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


CHAT_PROMPT = """# CRITICAL OUTPUT RULES (read these first, every turn)
1. NEVER write JSON in your reply. Not `{"name": ...}`, not `{"command": ...}`, not `{"function": ...}`. Tool calls go through the framework — you never type them as text.
2. If you want to call a tool, USE THE TOOL via the framework. If you can't, answer in plain English.
3. NEVER say "let me check" or "I'll look that up" — just answer or call the tool silently.

# Role
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

# Honesty
- If you don't know, say so. "I don't know" beats a confident wrong answer.
- Never invent facts about the user. Only use facts shown in RELEVANT MEMORIES — never fill gaps from training.
- Don't claim you "checked" or "looked up" something unless a tool result is in front of you.
- If RELEVANT DOCUMENTS are below and the answer is in them, cite [1], [2]. If not in them, don't pretend.

# Output rule
Never output JSON describing a tool call as your final reply. Either you call a tool (the framework handles that) OR you reply in plain prose. Never both narrating and pretending."""


CODER_PROMPT = """# CRITICAL OUTPUT RULES (read these first, every turn)
1. NEVER write JSON like `{"command": "..."}` or `{"name": ..., "parameters": ...}` in your reply. Tool calls go through the framework — they are NOT text.
2. To create a file: CALL `write_file(path, content)`. Do NOT paste code in your reply as a substitute. The disk is where code lives; the reply is for explaining what you did.
3. To run shell: CALL `shell_exec(command)`. Do NOT print the command in your reply.
4. If you find yourself about to type `{"...": "..."}`: STOP. Either call the tool, or answer in plain English. Never both.

# Role
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

# Honesty & hallucination guards
- **Code goes to disk, not into chat.** When the user asks you to create / write / save a file, you MUST call `write_file` or `edit_file`. Never paste the code in your reply as a substitute. The reply is for explaining what you did — the disk is where code lives.
- **Don't claim a file exists, was modified, or was committed unless a tool reported success.** Look at the tool result before describing it.
- **Don't invent file paths, function names, or library APIs you haven't seen.** If you didn't `read_file` it, don't quote from it. If you didn't `web_search` it, don't claim the docs say it.
- **If you don't know, say so.** "I don't see that in the codebase — want me to search?" beats a fabricated answer.
- **Match what the tool returned, not what you expected.** If `shell_exec` failed, the answer is "it failed: <error>", not "I ran it and it worked".

# Safety
Local file edits and runs are free to do. But for destructive or wide-blast operations — `rm -rf`, `git reset --hard`, force-push, dropping tables, deleting branches — confirm with the user first. Never use `--no-verify` to skip hooks unless the user explicitly says so. If a hook fails, fix the underlying issue.

# Output rule
Never output JSON pretending to be a tool call (`{"name": ..., "parameters": ...}`). Either you call a tool (the framework handles that) or you reply in plain prose / code. Never both."""


ULTRON_PROMPT = """# CRITICAL OUTPUT RULES (read these first, every turn)
1. NEVER write JSON in your reply. Not `{"name": ...}`, not `{"command": ...}`, not `{"function": ...}`. Tool calls go through the framework — never as text.
2. To do something: CALL the matching tool. If the tool doesn't exist, say so in plain English — don't pretend by writing JSON.
3. If asked "what can you do?": call `list_capabilities()`.
4. If you find yourself about to type `{"...": "..."}`: STOP. Either call the tool, or answer in plain English. Never both.

# Role
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
- Don't fabricate memories. If RELEVANT MEMORIES below has nothing about a topic, say "I don't have that on record" — don't guess from training data.

# Honesty
- Don't claim you did something unless a tool reported success. "I opened Firefox" only if `open_app` returned ok.
- Don't make up file paths, contacts, or settings. If you weren't told and a tool didn't return it, say you don't know.
- If a tool failed, report the failure honestly. Don't pretend it worked.

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
    r"read\s+file|write\s+file|edit\s+file|create\s+(?:a\s+|new\s+|the\s+)?file|delete\s+file|"
    r"new\s+file|save\s+(?:to|as|it)|save\s+(?:a\s+)?file|"
    r"list\s+(files|dir|folder)|grep\s|ripgrep|"
    r"run\s|execute|shell|bash|sudo|systemctl|docker|kubectl|npm\s|pip\s|apt\s|"
    r"play\s|pause|next\s+track|volume|brightness|mute|unmute|"
    r"clipboard|paste|copy\s+to|"
    r"refactor|implement|fix\s+bug|build\s+(a|me|the)|make\s+(?:a|me|the|new)|"
    r"create\s+(?:a|me|the|new|app|api|server|page|script|function|component|class|method|module|file)|"
    r"\.(?:py|js|ts|tsx|jsx|html|css|json|yaml|yml|md|txt|sh|sql|go|rs|java|cpp|rb|php)\b|"
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

_PLAY_RE = re.compile(r"^\s*(?:please\s+)?(play|resume)\s*(?:music|song|audio|media)?\s*[.!?]?\s*$", re.IGNORECASE)
_PAUSE_RE = re.compile(r"^\s*(?:please\s+)?(pause|stop)\s*(?:music|song|audio|media|playback)?\s*[.!?]?\s*$", re.IGNORECASE)
_NEXT_RE = re.compile(r"^\s*(?:please\s+)?(?:play\s+)?next\s*(?:song|track|tune)?\s*[.!?]?\s*$", re.IGNORECASE)
_PREV_RE = re.compile(r"^\s*(?:please\s+)?(?:play\s+)?(?:previous|prev|last)\s*(?:song|track|tune)?\s*[.!?]?\s*$", re.IGNORECASE)
_VOLUME_RE = re.compile(r"^\s*(?:please\s+)?(?:set\s+)?(?:the\s+)?volume\s+(?:to\s+|at\s+)?(?P<n>\d{1,3})%?\s*[.!?]?\s*$", re.IGNORECASE)
_VOLUME_REL_RE = re.compile(r"^\s*(?:please\s+)?(?P<dir>raise|lower|increase|decrease|turn\s+up|turn\s+down)\s+(?:the\s+)?volume\s*[.!?]?\s*$", re.IGNORECASE)
_MUTE_RE = re.compile(r"^\s*(?:please\s+)?mute\s*(?:the\s+)?(?:volume|sound|audio)?\s*[.!?]?\s*$", re.IGNORECASE)
_UNMUTE_RE = re.compile(r"^\s*(?:please\s+)?unmute\s*(?:the\s+)?(?:volume|sound|audio)?\s*[.!?]?\s*$", re.IGNORECASE)
_TYPE_RE = re.compile(r"^\s*(?:please\s+)?type\s+(?:the\s+text\s+|the\s+words?\s+)?[\"']?(?P<text>.+?)[\"']?\s*[.!?]?\s*$", re.IGNORECASE)
_PRESS_RE = re.compile(r"^\s*(?:please\s+)?press\s+(?:the\s+)?(?P<key>[\w\+\-]{1,30}(?:\s*\+\s*[\w\+\-]{1,30}){0,3})\s*(?:key)?\s*[.!?]?\s*$", re.IGNORECASE)
_SCROLL_RE = re.compile(r"^\s*(?:please\s+)?scroll\s+(?P<dir>up|down|left|right|to\s+top|to\s+bottom)\s*[.!?]?\s*$", re.IGNORECASE)
_NOTIFY_RE = re.compile(r"^\s*(?:please\s+)?notify\s+(?:me\s+)?(?:that\s+|with\s+)?[\"']?(?P<msg>.+?)[\"']?\s*[.!?]?\s*$", re.IGNORECASE)
_TIME_RE = re.compile(
    r"^\s*(?:please\s+)?("
    r"what(?:'s|s|\s+is)?\s+(?:the\s+)?time|"
    r"what\s+time\s+is\s+it|"
    r"tell\s+me\s+the\s+time|"
    r"current\s+time"
    r")\s*[.!?]?\s*$",
    re.IGNORECASE,
)
_BATTERY_RE = re.compile(r"^\s*(?:please\s+)?(?:what(?:'s|s|\s+is)?\s+(?:the\s+|my\s+)?battery|battery\s+(?:status|level|percent(?:age)?))\s*[.!?]?\s*$", re.IGNORECASE)


def _press_normalize(key: str) -> str:
    return re.sub(r"\s*\+\s*", "+", key.strip()).lower()


def _gated_tool_invoke(tool_name: str, args: dict, do_invoke):
    """Run a tool through the confirmation gate. Returns the result string.

    `do_invoke()` is a zero-arg callable that actually runs the tool. We split
    invocation from gating so callers can still pass complex args without us
    needing to reflect on them.
    """
    from agent.confirmations import confirm, get_context, _state
    if get_context() != "auto":
        arg_repr = ", ".join(f"{k}={repr(v)[:30]}" for k, v in (args or {}).items())[:160]
        if not confirm(tool_name, arg_repr):
            return f"[denied] user declined {tool_name}"
    return do_invoke()


def _intent_shortcut(message: str) -> dict | None:
    """Detect deterministic action commands so we don't depend on the LLM choosing a tool.

    Small models (3B) routinely fail to emit tool_calls and instead narrate or leak
    JSON. For high-confidence single-action requests, just run the tool directly —
    but route through the confirmation gate when one is active.

    Returns {"name": str, "args": str, "result": str} or None.
    """
    msg = message.strip()
    if not msg or len(msg) > 200:
        return None

    # If a confirmation context is active (voice or text), confirm at the
    # message level before we fire ANY shortcut. This prevents misheard / false
    # voice transcripts from auto-launching apps, taking screenshots, etc.
    from agent.confirmations import get_context, confirm
    if get_context() != "auto":
        # We don't know the specific tool yet — confirm using the user's words.
        if not confirm("voice command", msg[:120]):
            return {"name": "shortcut", "args": msg[:80], "result": "[denied] user declined"}

    if _SCREENSHOT_RE.match(msg):
        from agent.system_tools import screenshot
        return {"name": "screenshot", "args": "", "result": screenshot.invoke({})}

    if _TIME_RE.match(msg):
        from agent.system_tools import system_info
        info = system_info.invoke({})
        first = next((l for l in info.split("\n") if l.startswith("Time:")), info.splitlines()[0])
        return {"name": "system_info", "args": "time", "result": first}

    if _BATTERY_RE.match(msg):
        from agent.system_tools import system_info
        info = system_info.invoke({})
        bat = next((l for l in info.split("\n") if l.lower().startswith("battery")), None)
        return {"name": "system_info", "args": "battery", "result": bat or "No battery info available."}

    if _PLAY_RE.match(msg):
        from agent.system_tools import media_control
        return {"name": "media_control", "args": "play", "result": media_control.invoke({"action": "play-pause"})}

    if _PAUSE_RE.match(msg):
        from agent.system_tools import media_control
        return {"name": "media_control", "args": "pause", "result": media_control.invoke({"action": "pause"})}

    if _NEXT_RE.match(msg):
        from agent.system_tools import media_control
        return {"name": "media_control", "args": "next", "result": media_control.invoke({"action": "next"})}

    if _PREV_RE.match(msg):
        from agent.system_tools import media_control
        return {"name": "media_control", "args": "previous", "result": media_control.invoke({"action": "previous"})}

    m = _VOLUME_RE.match(msg)
    if m:
        from agent.system_tools import set_volume
        n = max(0, min(100, int(m.group("n"))))
        return {"name": "set_volume", "args": str(n), "result": set_volume.invoke({"percent": n})}

    m = _VOLUME_REL_RE.match(msg)
    if m:
        from agent.system_tools import set_volume
        direction = m.group("dir").lower()
        delta = 15 if any(w in direction for w in ("up", "raise", "increase")) else -15
        # We don't know current, so just nudge to a sane value.
        target = 75 if delta > 0 else 25
        return {"name": "set_volume", "args": str(target), "result": set_volume.invoke({"percent": target})}

    if _MUTE_RE.match(msg):
        from agent.system_tools import set_volume
        return {"name": "set_volume", "args": "0", "result": set_volume.invoke({"percent": 0})}

    if _UNMUTE_RE.match(msg):
        from agent.system_tools import set_volume
        return {"name": "set_volume", "args": "60", "result": set_volume.invoke({"percent": 60})}

    m = _TYPE_RE.match(msg)
    if m:
        from agent.system_tools import type_text
        text = m.group("text").strip().strip("'\"")
        if text and len(text) < 500:
            return {"name": "type_text", "args": text[:80], "result": type_text.invoke({"text": text})}

    m = _PRESS_RE.match(msg)
    if m:
        from agent.system_tools import press_key
        key = _press_normalize(m.group("key"))
        return {"name": "press_key", "args": key, "result": press_key.invoke({"key": key})}

    m = _SCROLL_RE.match(msg)
    if m:
        from agent.system_tools import press_key
        direction = m.group("dir").lower()
        key_map = {
            "up": "Page_Up", "down": "Page_Down",
            "left": "Home", "right": "End",
            "to top": "ctrl+Home", "to bottom": "ctrl+End",
        }
        key = key_map.get(direction, "Page_Down")
        return {"name": "press_key", "args": key, "result": press_key.invoke({"key": key})}

    m = _NOTIFY_RE.match(msg)
    if m:
        from agent.system_tools import notify
        body = m.group("msg").strip().strip("'\"")
        if body and len(body) < 280:
            return {"name": "notify", "args": body[:60], "result": notify.invoke({"title": "Ultron", "message": body})}

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


_LEAKED_TOOL_RE = re.compile(
    r"```(?:json)?\s*(\{[\s\S]*?\})\s*```|^\s*(\{[\s\S]+?\})\s*$",
    re.MULTILINE,
)

# Heuristic mapping: arg-shape → preferred tool name. Used when the model leaks
# a bare args dict like `{"command": "touch X"}` without a `name` field.
_BARE_ARGS_TOOL = [
    ({"command"},                        "shell_exec"),
    ({"path", "content"},                "write_file"),
    ({"path", "old", "new"},             "edit_file"),
    ({"path"},                           "read_file"),
    ({"name"},                           "open_app"),
    ({"url"},                            "open_url"),
    ({"text"},                           "type_text"),
    ({"key"},                            "press_key"),
    ({"percent"},                        "set_volume"),
    ({"action"},                         "media_control"),
    ({"query"},                          "web_search"),
    ({"expression"},                     "calculator"),
    ({"code"},                           "python_exec"),
    ({"title", "message"},               "notify"),
]


def _parse_leaked_json(text: str) -> dict | None:
    """Pull out a JSON object the model emitted as text. Returns parsed dict or None."""
    import json
    if not text:
        return None
    s = text.strip().strip("`").strip()
    # Try the whole thing first.
    if s.startswith("{"):
        try:
            return json.loads(s)
        except Exception:
            # Try truncating to the first balanced brace.
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
            if end > 0:
                try:
                    return json.loads(s[:end])
                except Exception:
                    pass
    # Try matching a fenced JSON block.
    m = _LEAKED_TOOL_RE.search(text)
    if m:
        raw = m.group(1) or m.group(2)
        try:
            return json.loads(raw)
        except Exception:
            return None
    return None


def _resolve_tool(tools, name: str):
    """Find a tool by name in the agent's tool list."""
    name = (name or "").strip().lower()
    if not name:
        return None
    for t in tools or []:
        tname = (getattr(t, "name", "") or "").lower()
        if tname == name:
            return t
    return None


def _guess_tool_from_args(tools, args: dict):
    """Guess which tool the leaked dict was meant for, by arg-shape match."""
    keys = set(args.keys())
    for required, tool_name in _BARE_ARGS_TOOL:
        if required.issubset(keys):
            t = _resolve_tool(tools, tool_name)
            if t is not None:
                return t, tool_name
    return None, None


def _execute_leaked_tool_call(text: str, tools) -> tuple[str, str, str] | None:
    """If `text` is a leaked tool-call JSON, execute the matching tool.

    Returns (tool_name, args_repr, result_text) on success, or None if we
    couldn't make sense of it / no matching tool is in the agent's set.
    """
    parsed = _parse_leaked_json(text)
    if not isinstance(parsed, dict):
        return None

    tool = None
    args = parsed
    name = ""

    # Wrapped form: {"name": "X", "parameters": {...}} or {"function": ...} / {"tool": ...}
    if "name" in parsed and isinstance(parsed.get("parameters"), dict):
        name = str(parsed["name"])
        tool = _resolve_tool(tools, name)
        args = parsed["parameters"]
    elif "function" in parsed and isinstance(parsed.get("arguments"), dict):
        name = str(parsed["function"])
        tool = _resolve_tool(tools, name)
        args = parsed["arguments"]
    elif "tool" in parsed and isinstance(parsed.get("input"), dict):
        name = str(parsed["tool"])
        tool = _resolve_tool(tools, name)
        args = parsed["input"]
    else:
        # Bare-args form — guess from shape.
        tool, name = _guess_tool_from_args(tools, parsed)

    if tool is None:
        return None

    try:
        result = tool.invoke(args)
    except Exception as e:
        result = f"[error invoking {name}: {e}]"

    arg_repr = ", ".join(f"{k}={repr(v)[:40]}" for k, v in (args or {}).items())[:200]
    return name, arg_repr, str(result)[:1000]


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


_CODER_VERB_RE = re.compile(
    r"\b(make|create|build|write|generate|add|set\s+up|setup|put|save|drop|"
    r"fix|bug|error|broken|not\s+working|fails?|crash|"
    r"refactor|rename|move|extract|inline|"
    r"explain|show|trace|find|locate|where|how\s+(?:do|can|does)|"
    r"read|open|edit|change|update|modify|"
    r"run|execute|test|check|verify|"
    r"install|setup|configure|deploy|"
    r"commit|push|pull|merge|branch|"
    r"\.(?:py|js|ts|tsx|jsx|html|css|json|yaml|yml|md|sh|sql|go|rs|java|cpp|rb|php)\b|"
    r"function|class|method|component|module|api|endpoint|route|model|controller|"
    r"react|vue|svelte|fastapi|express|django|flask"
    r")\b",
    re.IGNORECASE,
)


def _is_chat_only(message: str, mode: str = "chat") -> bool:
    """Conversational input that doesn't need any tool — answer directly with the LLM.

    In coder mode we are MUCH stricter: only pure greetings/thanks bypass the agent.
    Coder mode exists to do work — substantive requests must hit the tools."""
    if _is_chitchat(message):
        return True
    msg = message.strip()
    if len(msg) > 250:
        return False
    if _TOOL_HINT_RE.search(msg):
        return False
    if mode == "coder" and _CODER_VERB_RE.search(msg):
        return False
    return True


def _chat_reply(message: str, mode: str = "chat") -> str:
    """Direct LLM call with no tools — friendly conversational reply.

    Greetings skip context entirely (cheap & fast). Self-referential questions
    take a deterministic path — if memory has nothing, we refuse instead of
    letting the LLM hallucinate. Otherwise full memory+RAG context is injected.
    """
    if is_self_referential(message):
        facts = lookup_self_facts(message)
        if not facts:
            return refusal_for_self_question(message)
        # Have facts — fall through to the normal LLM path with context, so the
        # answer is phrased naturally instead of a raw fact dump.

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

    if _is_chat_only(message, mode=mode):
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
        executed = _execute_leaked_tool_call(final, tools)
        if executed is not None:
            _, _, result = executed
            final = result
        else:
            cleaned = _strip_fake_tool_call(final).strip()
            final = cleaned if cleaned else _retry_plain_reply(message)

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

    if _is_chat_only(message, mode=mode):
        reply = _chat_reply(message, mode=mode)
        yield {"type": "router", "data": {"categories": ["chat"], "tool_count": 0}}
        yield {"type": "token", "data": reply}
        yield {"type": "final", "data": reply}
        return

    base_prompt = _prompt_for(mode)
    mem = _full_context(message)

    if mode == "ultron":
        cats = route(message)
        tools = tools_for_categories(cats)
        yield {"type": "router", "data": {"categories": list(cats), "tool_count": len(tools)}}
    else:
        tools = CODER_TOOLS if mode == "coder" else CHAT_TOOLS

    if _confirm_ctx() != "auto":
        tools = _gate_tools(tools)

    agent = create_react_agent(_llm(), tools=tools, prompt=base_prompt + mem)

    msgs = []
    for m in history or []:
        msgs.append((m["role"], m["content"]))
    msgs.append(("user", message))

    final_text = ""
    tool_calls_made: list[dict] = []
    try:
        for event in agent.stream({"messages": msgs}, stream_mode="updates"):
            for node, payload in event.items():
                for msg in payload.get("messages", []):
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            data = {
                                "name": tc.get("name", "?"),
                                "args": str(tc.get("args", ""))[:200],
                            }
                            tool_calls_made.append(data)
                            yield {"type": "tool_call", "data": data}
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
        executed = _execute_leaked_tool_call(final_text, tools)
        if executed is not None:
            tool_name, arg_repr, result = executed
            tool_calls_made.append({"name": tool_name, "args": arg_repr})
            yield {"type": "tool_call", "data": {"name": tool_name, "args": arg_repr}}
            yield {"type": "tool_result", "data": {"name": tool_name, "content": result[:300]}}
            final_text = result
            yield {"type": "token", "data": final_text}
        else:
            cleaned = _strip_fake_tool_call(final_text).strip()
            if cleaned:
                final_text = cleaned
            else:
                final_text = _retry_plain_reply(message)
            yield {"type": "token", "data": final_text}

    if is_code_in_chat_failure(message, final_text, tool_calls_made, mode):
        yield {"type": "tool_result", "data": {
            "name": "grounding_check",
            "content": "code-in-chat detected — retrying with forced write_file",
        }}
        retry_text = ""
        for ev in _retry_force_write_file(message, history, mode):
            if ev["type"] == "tool_call":
                tool_calls_made.append(ev["data"])
            if ev["type"] == "token":
                retry_text = ev["data"]
            yield ev
        if retry_text:
            final_text = retry_text

    yield {"type": "final", "data": final_text}


def _retry_force_write_file(message: str, history, mode: str) -> Iterator[dict]:
    """One retry with a hardened prompt that demands write_file is called."""
    if mode != "coder":
        return
    forcing = (
        "\n\n# CRITICAL\nThe user asked you to CREATE/WRITE a file. You MUST call "
        "`write_file(path, content)` to put the code on disk. Do NOT paste the code "
        "in your reply — call the tool. Your reply text should describe what you wrote, "
        "not contain the code itself."
    )
    base_prompt = _prompt_for(mode) + forcing
    mem = _full_context(message)
    tools = CODER_TOOLS

    agent = create_react_agent(_llm(), tools=tools, prompt=base_prompt + mem)
    msgs = []
    for m in history or []:
        msgs.append((m["role"], m["content"]))
    msgs.append(("user", message))

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
                            yield {"type": "token", "data": strip_thinking(msg.content)}
    except Exception as e:
        yield {"type": "error", "data": f"retry failed: {e}"}
