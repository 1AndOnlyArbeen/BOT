"""Self-reflection critic — runs after the agent answers. Verifies the response actually
addresses the request and patches half-finished work without a full re-run."""
from __future__ import annotations

import re
from functools import lru_cache

from langchain_ollama import ChatOllama

from config import LLM_MODEL


CRITIC_PROMPT = """You are a quality critic. The user asked for X; the assistant produced Y.

Evaluate Y against X strictly:
- Did the assistant complete the task or stop early?
- Is the answer accurate, or are claims unverified?
- For code requests: is the code actually present and runnable?
- For action requests: was the action taken or just described?

Output ONLY one of:
OK
or
RETRY: <one short sentence describing what the assistant should fix or add>

User request: {request}

Assistant answer:
{answer}

Verdict:"""


_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)


@lru_cache(maxsize=1)
def _critic_llm():
    return ChatOllama(model=LLM_MODEL, temperature=0.0, num_predict=120)


def critique(request: str, answer: str) -> tuple[bool, str]:
    """Returns (ok, feedback). ok=False with feedback means retry needed."""
    if not answer or len(answer) < 10:
        return False, "Answer is empty or too short."
    try:
        resp = _critic_llm().invoke(
            CRITIC_PROMPT.format(request=request[:1500], answer=answer[:2500])
        ).content
    except Exception:
        return True, ""
    text = _THINK.sub("", resp).strip().upper()
    if text.startswith("OK"):
        return True, ""
    if text.startswith("RETRY"):
        return False, resp.split(":", 1)[1].strip() if ":" in resp else "Improve the answer."
    return True, ""


def reflect_and_patch(request: str, answer: str, agent_runner, max_retries: int = 1) -> str:
    """If the answer is bad, ask the agent to patch it once with the critic's feedback."""
    ok, fb = critique(request, answer)
    if ok:
        return answer
    for _ in range(max_retries):
        followup = (
            f"Your previous answer was incomplete. Critic feedback: {fb}\n\n"
            f"Original request: {request}\n\n"
            f"Improve and produce the final corrected answer."
        )
        new_answer = agent_runner(followup)
        ok2, _ = critique(request, new_answer)
        if ok2:
            return new_answer
        answer = new_answer
    return answer
