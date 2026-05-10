"""Detect and capture user corrections.

When the user starts a turn with "no", "wrong", "actually", "that's not
right", we treat the rest as a correction of the previous answer. The
correction gets:

  - persisted as a durable fact (via agent.learning.remember) with
    "Correction:" prefix so it ranks high on future recalls,
  - surfaced to the model in the system prompt for THIS turn so it
    immediately adjusts.

The correction trigger is conservative on purpose — false positives waste
durable memory slots, so we only fire on clear lead-ins.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from agent.learning import remember


_CORRECTION_LEAD = re.compile(
    r"^\s*(no+[\s,.!]+|wrong[\s,.!]+|nope[\s,.!]+|actually[\s,.!]*|"
    r"that'?s?\s+(not\s+(right|correct)|wrong)[\s,.!]*|"
    r"incorrect[\s,.!]*|"
    r"you'?re\s+wrong[\s,.!]*|"
    r"you\s+got\s+it\s+wrong[\s,.!]*|"
    r"that\s+is\s+(not|incorrect|wrong)[\s,.!]*)",
    re.IGNORECASE,
)


@dataclass
class Correction:
    detected: bool
    correction_text: str = ""

    def system_prompt_block(self) -> str:
        if not self.detected or not self.correction_text:
            return ""
        return (
            "\n\n# ⚠ User correction this turn\n"
            f"The user is correcting your previous answer. Their correction:\n"
            f"\"{self.correction_text}\"\n"
            "Acknowledge the mistake briefly, then give the corrected answer. "
            "Do NOT repeat the wrong answer."
        )


def detect(message: str) -> Correction:
    """Return a Correction record. Empty/non-detected if no trigger fires."""
    msg = (message or "").strip()
    m = _CORRECTION_LEAD.match(msg)
    if not m:
        return Correction(detected=False)

    rest = msg[m.end():].strip()
    rest = rest.lstrip("-—:•").strip()
    if len(rest) < 4:
        # The user said "no" but gave no correction body — useful signal still.
        return Correction(detected=True, correction_text="(user said the previous reply was wrong but gave no detail)")
    return Correction(detected=True, correction_text=rest[:400])


def persist(correction: Correction) -> bool:
    """Persist the correction as a durable fact. Returns True if saved."""
    if not correction.detected or not correction.correction_text:
        return False
    body = correction.correction_text
    fact = f"Correction: {body}"
    try:
        return bool(remember([fact]))
    except Exception:
        return False
