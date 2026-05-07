"""Wrap every LangChain tool to auto-log calls + outcomes.

Logs to audit DB and feeds tool_learning success signals."""
from __future__ import annotations

import time
from typing import Any

from langchain_core.tools import BaseTool

from agent import audit
from agent import tool_learning


def _success_from_result(result: Any) -> bool:
    s = str(result)
    if not s.strip():
        return False
    low = s.lower()
    if "[error]" in low or "[timeout]" in low or "[not found]" in low:
        return False
    if low.startswith("error") or low.startswith("⚠"):
        return False
    return True


def wrap(tool: BaseTool, category_hint: str = "") -> BaseTool:
    """Wrap a single tool's invoke method with audit + learning hooks."""
    if getattr(tool, "_ultron_wrapped", False):
        return tool

    original_run = tool.invoke

    def wrapped_invoke(input: Any, config: Any = None, **kwargs: Any):
        t0 = time.time()
        status = "ok"
        result: Any = ""
        try:
            result = original_run(input, config, **kwargs)
            success = _success_from_result(result)
            status = "ok" if success else "warn"
        except Exception as e:
            success = False
            status = "error"
            result = f"[exception] {type(e).__name__}: {e}"
            elapsed_ms = (time.time() - t0) * 1000
            audit.log(
                tool=tool.name,
                args=input if isinstance(input, dict) else {"input": str(input)[:300]},
                result=str(result)[:1500],
                duration_ms=elapsed_ms,
                status=status,
            )
            if category_hint:
                tool_learning.record_outcome(category_hint, tool.name, False)
            raise

        elapsed_ms = (time.time() - t0) * 1000
        audit.log(
            tool=tool.name,
            args=input if isinstance(input, dict) else {"input": str(input)[:300]},
            result=str(result)[:1500],
            duration_ms=elapsed_ms,
            status=status,
        )
        if category_hint:
            tool_learning.record_outcome(category_hint, tool.name, success)
        return result

    object.__setattr__(tool, "invoke", wrapped_invoke)
    object.__setattr__(tool, "_ultron_wrapped", True)
    return tool


def wrap_all(tools: list, category_hint: str = "") -> list:
    return [wrap(t, category_hint=category_hint) for t in tools]
