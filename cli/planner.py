"""Tiny LLM-powered planner for non-trivial coder turns.

Used by cli.agent for `edit` and `init` intents. The planner produces a
short ordered list of steps tailored to the actual request, falling back
to a heuristic outline if the LLM call errors or the output is unusable.

Kept tiny on purpose — one LLM call, capped context, capped output. The
goal is a frame the model can fill in, not a full plan-and-execute system.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from langchain_ollama import ChatOllama

from config import LLM_MODEL


@dataclass
class PlanStep:
    index: int
    goal: str


Intent = Literal["question", "read", "edit", "run", "init", "chat"]


_PLANNER_SYSTEM = (
    "You are an expert engineer's planner. Given the user's coding request, "
    "produce 3 to 6 concrete next steps. Each step should be a single short "
    "imperative sentence (under 12 words). NO numbering, NO commentary, NO "
    "explanation — one step per line. Steps should be specific to the request "
    "(reference real file names if mentioned). The first step is what to do "
    "right now; the last step is the verification."
)


_HEURISTIC: dict[Intent, list[str]] = {
    "edit": [
        "Find the target file with grep_files / find_files.",
        "Read the relevant section with read_file.",
        "Apply a surgical change with edit_file.",
        "Run the code or its tests to verify.",
    ],
    "init": [
        "Plan the file layout in 1–2 sentences.",
        "Create directories with make_folder.",
        "Write each file with write_file.",
        "Install deps if needed via shell_exec.",
        "Smoke-test the result.",
    ],
    "run": [
        "Pick the right execution tool (python_exec / run_python_file / shell_exec).",
        "Run it and report what happened in one line.",
    ],
    "read": [
        "Locate the file (grep_files / find_files / codebase_search).",
        "Read the section and quote the lines as path:line.",
    ],
}


def _heuristic_steps(intent: Intent) -> list[PlanStep]:
    raw = _HEURISTIC.get(intent, [])
    return [PlanStep(i + 1, s) for i, s in enumerate(raw)]


def _parse_steps(text: str) -> list[PlanStep]:
    out: list[PlanStep] = []
    if not text:
        return out
    for line in text.splitlines():
        s = line.strip().strip("-•*").strip()
        s = re.sub(r"^\(?\d+\)?[.)\s-]+", "", s).strip()
        s = s.rstrip(".")
        if not s or len(s) < 4 or len(s) > 200:
            continue
        out.append(PlanStep(len(out) + 1, s))
        if len(out) >= 6:
            break
    return out


def make_plan(message: str, intent: Intent) -> list[PlanStep]:
    """Return a per-turn plan. LLM-generated for edit/init, heuristic otherwise."""
    if intent in ("chat", "question"):
        return []
    if intent not in ("edit", "init"):
        return _heuristic_steps(intent)

    try:
        llm = ChatOllama(model=LLM_MODEL, temperature=0.3, num_predict=160, num_ctx=1024)
        out = llm.invoke([
            ("system", _PLANNER_SYSTEM),
            ("user", message),
        ]).content
    except Exception:
        return _heuristic_steps(intent)

    steps = _parse_steps(out)
    if len(steps) < 2:
        # Bad output — fall back so we don't ship an empty plan.
        return _heuristic_steps(intent)
    return steps
