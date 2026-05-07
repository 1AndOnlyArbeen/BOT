"""Anti-hallucination guards.

Small local models hallucinate in three predictable ways:

1. **Empty-memory speculation.** Asked "who is arbin?" with nothing in the
   memory store, the model invents from training data. Fix: detect
   self-referential questions, look up directly, and refuse explicitly when
   nothing matches — instead of letting the LLM fill the gap.

2. **Code-in-chat.** In coder mode, asked to "create a file", the model
   sometimes prints code in the reply instead of calling `write_file`. Fix:
   after the agent finishes, detect "reply contains a code block but no
   write_file/edit_file tool call happened" and either retry or flag.

3. **Tool-output drift.** Agent runs a tool, then summarizes incorrectly.
   Mitigated upstream by tool-result events being shown verbatim.

The functions below are pure / regex-based — cheap to call on every turn.
"""
from __future__ import annotations

import re
from typing import Iterable

from agent.learning import recall


_SELF_REFERENTIAL_RE = re.compile(
    r"\b("
    r"who\s+(?:am\s+i|is\s+(?:arbin|santosh|me))|"
    r"what(?:'s|\s+is|s|\s+are)?\s+my\s+\w+|"
    r"where(?:'s|\s+is|\s+do)?\s+(?:i|my)\s+\w+|"
    r"do\s+you\s+(?:know|remember)\s+(?:my|me|about\s+me)|"
    r"what\s+do\s+you\s+know\s+about\s+me|"
    r"tell\s+me\s+about\s+(?:me|myself)|"
    r"recall(?:\s+(?:about\s+)?(?:me|my\s+\w+))?|"
    r"check\s+(?:your\s+)?memory|"
    r"what\s+have\s+i\s+told\s+you"
    r")\b",
    re.IGNORECASE,
)


def is_self_referential(message: str) -> bool:
    """The user is asking about themselves — answer must come from memory, not training data."""
    return bool(_SELF_REFERENTIAL_RE.search(message or ""))


def lookup_self_facts(message: str, k: int = 5, min_hits: int = 1) -> list[str]:
    """Pull memories about the user that match the question. Empty list = we don't know."""
    hits = recall(message, k=k)
    # Filter to hits that look like personal facts (start with "User" / contain "user").
    personal = [h for h in hits if "user" in h.lower()[:20]]
    if len(personal) < min_hits:
        return []
    return personal


def refusal_for_self_question(message: str) -> str:
    """Deterministic refusal text when memory has nothing matching."""
    msg = message.lower()
    if "name" in msg:
        return "I don't have your name on record. Tell me — say 'remember that my name is …' and I'll keep it."
    if "email" in msg:
        return "I don't have an email saved for you. Try: 'remember that my email is …'"
    if "remember" in msg or "memory" in msg or "recall" in msg:
        return "I don't have anything saved about that. You can teach me with 'remember that …'."
    return (
        "I don't have that on record yet. Tell me directly — for example, "
        "'remember that my name is …' or 'remember that I work at …' — and I'll keep it for next time."
    )


_CODE_BLOCK_RE = re.compile(r"```[\w]*\n[\s\S]+?```", re.MULTILINE)
_INLINE_LANG_HINT_RE = re.compile(
    r"```(jsx|tsx|js|ts|py|python|html|css|json|yaml|sh|bash|sql|go|rust|rs|java|cpp|c\+\+|ruby|rb|php)",
    re.IGNORECASE,
)


def reply_contains_code_block(reply: str) -> bool:
    """True if the assistant reply has a fenced code block."""
    return bool(_CODE_BLOCK_RE.search(reply or ""))


def reply_contains_substantive_code(reply: str) -> bool:
    """True if the reply has a code block with a recognized language tag (likely meant for a file)."""
    return bool(_INLINE_LANG_HINT_RE.search(reply or ""))


def used_file_writer(tool_calls: Iterable[dict]) -> bool:
    """True if any of the tool calls in this turn wrote/edited a file."""
    writers = {"write_file", "edit_file", "create_file", "save_code_pattern"}
    for tc in tool_calls or []:
        name = (tc or {}).get("name") or ""
        if name in writers:
            return True
    return False


def is_code_in_chat_failure(message: str, reply: str, tool_calls: Iterable[dict], mode: str) -> bool:
    """User asked to create/write/save a file → reply has substantive code → no write_file fired."""
    if mode != "coder":
        return False
    intent_re = re.compile(
        r"\b(create|make|write|generate|save|new)\s+(?:a\s+|the\s+|me\s+a\s+)?(?:new\s+)?"
        r"(?:file|component|module|class|function|script|page|route|api|endpoint)\b",
        re.IGNORECASE,
    )
    if not intent_re.search(message or ""):
        # Also catch "create Foo.jsx" / "make Bar.py"
        ext_re = re.compile(r"\b(create|make|write|generate|save|new)\b.*\.\w{1,4}\b", re.IGNORECASE)
        if not ext_re.search(message or ""):
            return False
    if not reply_contains_substantive_code(reply):
        return False
    return not used_file_writer(tool_calls)
