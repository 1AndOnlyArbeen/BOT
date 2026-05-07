"""Per-tool confirmation gate.

Wraps risky tools so they ask the user before executing. Works in three I/O contexts:

- **text**:   reads Y/N from stdin (CLI REPL default)
- **voice**:  speaks the question via TTS, transcribes the answer via STT
- **auto**:   no prompt, always approve (web mode default — UI handles its own prompts)

Approval modes per tool:
- "once":     ask every single call
- "session":  ask once, remember for this process lifetime
- "never":    auto-approve (whitelisted)
- "deny":     always reject without asking

The gate is set per-process via `set_context()` and `set_mode_for()`.

Tool tiers come from `agent/permissions.py`:
  read    → never prompt (safe)
  write   → prompt by default
  system  → prompt by default
  network → prompt by default
  risky   → prompt by default

Read tools are always allowed silently.
"""
from __future__ import annotations

import os
import re
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field

from agent.permissions import tier_of


_lock = threading.Lock()


@dataclass
class ConfirmState:
    context: str = "auto"  # "text" | "voice" | "auto"
    approvals: dict[str, str] = field(default_factory=dict)  # tool_name → mode
    deny: set[str] = field(default_factory=set)
    require_tiers: tuple[str, ...] = ("write", "system", "network", "risky")


_state = ConfirmState()


def set_context(ctx: str) -> None:
    """Where confirmations should be asked: text, voice, or auto-approve."""
    if ctx not in ("text", "voice", "auto"):
        return
    with _lock:
        _state.context = ctx


def get_context() -> str:
    return _state.context


def set_mode_for(tool_name: str, mode: str) -> None:
    """mode: 'once' | 'session' | 'never' | 'deny'."""
    if mode not in ("once", "session", "never", "deny"):
        return
    with _lock:
        if mode == "deny":
            _state.deny.add(tool_name)
            _state.approvals.pop(tool_name, None)
        else:
            _state.deny.discard(tool_name)
            _state.approvals[tool_name] = mode


def reset_session() -> None:
    """Forget all session-level 'always' approvals (denials persist)."""
    with _lock:
        _state.approvals.clear()


def get_approvals() -> dict[str, str]:
    with _lock:
        out = dict(_state.approvals)
        for d in _state.deny:
            out[d] = "deny"
        return out


def needs_confirm(tool_name: str) -> bool:
    """True if calling this tool should prompt the user."""
    if _state.context == "auto":
        return False
    if tool_name in _state.deny:
        return True  # we'll prompt and deny
    pre = _state.approvals.get(tool_name)
    if pre == "never" or pre == "session":
        return False
    return tier_of(tool_name) in _state.require_tiers


# ─────────────────── prompts ───────────────────
_YES_RE = re.compile(r"\b(yes|yep|yeah|y|ok|okay|sure|do\s+it|go\s+ahead|approve|allow)\b", re.IGNORECASE)
_NO_RE = re.compile(r"\b(no|nope|nah|n|stop|cancel|deny|don'?t|reject|abort)\b", re.IGNORECASE)
_ALWAYS_RE = re.compile(r"\b(always|every\s+time|all|session|forever)\b", re.IGNORECASE)


def _format_question(tool_name: str, args: str) -> str:
    short_args = args[:120].replace("\n", " ")
    if short_args:
        return f"Run {tool_name}({short_args})?"
    return f"Run {tool_name}?"


def _ask_text(question: str) -> str:
    """Read [y/n/always/never] from stdin."""
    print()
    print(f"  ⚠ {question}")
    try:
        return input("    [y]es / [n]o / [a]lways / never › ").strip()
    except (EOFError, KeyboardInterrupt):
        return "n"


def _ask_voice(question: str) -> str:
    """Speak the question, transcribe the spoken answer."""
    try:
        from voice.tts import speak
        from voice.jarvis import _record_seconds, _transcribe
    except Exception:
        return _ask_text(question)
    try:
        speak(question + " Yes or no?")
    except Exception:
        pass
    try:
        wav = _record_seconds(seconds=4)
        return _transcribe(wav)
    except Exception:
        return ""


def _interpret(answer: str) -> tuple[bool, str | None]:
    """Returns (allowed, persist_mode_or_None)."""
    a = (answer or "").strip().lower()
    if not a or a in {"n", "no"}:
        return False, None
    if a.startswith("never"):
        return False, "deny"
    if a in {"a", "always"} or _ALWAYS_RE.search(a):
        return True, "session"
    if a in {"y", "yes"} or _YES_RE.search(a):
        return True, "once"
    if _NO_RE.search(a):
        return False, None
    # ambiguous — be safe, deny
    return False, None


def confirm(tool_name: str, args: str) -> bool:
    """Synchronously ask the user. Updates state if they say 'always' or 'never'."""
    if not needs_confirm(tool_name):
        return tool_name not in _state.deny
    question = _format_question(tool_name, args)
    if _state.context == "voice":
        answer = _ask_voice(question)
    else:
        answer = _ask_text(question)
    allowed, persist = _interpret(answer)
    if persist:
        set_mode_for(tool_name, persist)
    return allowed


# ─────────────────── tool wrapping ───────────────────
def wrap_tools(tools: list, *, allow_tiers: tuple[str, ...] = ("read",)) -> list:
    """Return a copy of `tools` where non-allow_tiers tools first call the gate.

    Wrapping happens by intercepting the tool's underlying function. langchain's
    StructuredTool exposes `.func`; we replace it with a gate-then-delegate wrapper.
    """
    out = []
    for t in tools:
        name = getattr(t, "name", None) or str(t)
        if tier_of(name) in allow_tiers:
            out.append(t)
            continue
        out.append(_gated(t))
    return out


def _gated(tool):
    """Replace tool.func with a wrapper that prompts before invoking."""
    name = getattr(tool, "name", "?")
    inner = getattr(tool, "func", None)
    if inner is None:
        return tool

    def gated_call(*args, **kwargs):
        arg_repr = ", ".join(
            [repr(a)[:40] for a in args] + [f"{k}={repr(v)[:40]}" for k, v in kwargs.items()]
        )
        if not confirm(name, arg_repr):
            return f"[denied] user declined {name}"
        return inner(*args, **kwargs)

    gated_call.__name__ = inner.__name__
    gated_call.__doc__ = inner.__doc__
    try:
        tool.func = gated_call
    except Exception:
        pass
    return tool


@contextmanager
def context(ctx: str):
    prev = get_context()
    set_context(ctx)
    try:
        yield
    finally:
        set_context(prev)
