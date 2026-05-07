"""Tool catalogues per agent mode. Massive Ultron toolset."""
from __future__ import annotations

import io
import math
import contextlib
import multiprocessing as mp
from typing import Any

from langchain_core.tools import tool

from rag.retriever import search as rag_search_impl
from agent.file_tools import FILE_TOOLS
from agent.system_tools import SYSTEM_TOOLS
from agent.comm_tools import COMM_TOOLS
from agent.vision_tools import VISION_TOOLS
from agent.web_tools import WEB_FETCH_TOOLS
from agent.mouse_tools import MOUSE_TOOLS
from agent.file_search import FILE_SEARCH_TOOLS
from agent.process_tools import PROCESS_NETWORK_TOOLS
from agent.scheduler import SCHEDULER_TOOLS
from agent.media_tools import MEDIA_TOOLS
from agent.git_tools import GIT_TOOLS
from agent.document_tools import DOCUMENT_TOOLS
from agent.dev_tools import DEV_TOOLS
from agent.browser_automation import BROWSER_TOOLS
from agent.vision_llm import VISION_LLM_TOOLS
from agent.gui_smart import GUI_SMART_TOOLS
from agent.calendar_tools import CALENDAR_TOOLS
from agent.code_library import CODE_LIBRARY_TOOLS
from agent.email_tools import EMAIL_TOOLS
from agent.database_tools import DATABASE_TOOLS
from agent.github_tools import GITHUB_TOOLS
from agent.api_client import API_CLIENT_TOOLS
from agent.spreadsheet_tools import SPREADSHEET_TOOLS
from agent.codebase_tools import CODEBASE_TOOLS
from agent.shell_tools import SHELL_TOOLS
from agent.learn_topic import LEARN_TOPIC_TOOLS
from config import WEB_SEARCH_RESULTS


@tool
def web_search(query: str) -> str:
    """Search the live web via DuckDuckGo."""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return "[web_search] duckduckgo-search not installed."
    try:
        with DDGS() as ddgs:
            hits = list(ddgs.text(query, max_results=WEB_SEARCH_RESULTS))
    except Exception as e:
        return f"[web_search error] {e}"
    if not hits:
        return "No web results."
    return "\n\n".join(
        f"[{i}] {h.get('title','')}\n{h.get('href','')}\n{h.get('body','')}"
        for i, h in enumerate(hits, 1)
    )


@tool
def rag_search(query: str) -> str:
    """Search the user's uploaded documents."""
    return rag_search_impl(query)


@tool
def calculator(expression: str) -> str:
    """Evaluate a math expression."""
    allowed = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
    allowed.update({"abs": abs, "round": round, "min": min, "max": max})
    try:
        return str(eval(expression, {"__builtins__": {}}, allowed))
    except Exception as e:
        return f"[calc error] {e}"


def _run_user_code(code: str, q):
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            exec(code, {"__builtins__": __builtins__})
        q.put(("ok", buf.getvalue() or "(no output)"))
    except Exception as e:
        q.put(("err", f"{buf.getvalue()}\n{type(e).__name__}: {e}"))


@tool
def python_exec(code: str) -> str:
    """Execute Python code in an isolated subprocess (10s timeout)."""
    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    p = ctx.Process(target=_run_user_code, args=(code, q))
    p.start()
    p.join(timeout=10)
    if p.is_alive():
        p.terminate()
        p.join()
        return "[python_exec] timeout after 10s"
    if not q.empty():
        status, out = q.get()
        prefix = "" if status == "ok" else "[error]\n"
        return prefix + out[:4000]
    return "[python_exec] no output"


KNOWLEDGE_TOOLS = [rag_search, web_search, calculator, python_exec]

from agent.auto_audit import wrap_all

KNOWLEDGE_TOOLS = wrap_all(KNOWLEDGE_TOOLS, category_hint="knowledge")
SYSTEM_TOOLS = wrap_all(SYSTEM_TOOLS, category_hint="system")
COMM_TOOLS = wrap_all(COMM_TOOLS, category_hint="comm")
VISION_TOOLS = wrap_all(VISION_TOOLS, category_hint="vision")
VISION_LLM_TOOLS = wrap_all(VISION_LLM_TOOLS, category_hint="vision_llm")
GUI_SMART_TOOLS = wrap_all(GUI_SMART_TOOLS, category_hint="vision")
WEB_FETCH_TOOLS = wrap_all(WEB_FETCH_TOOLS, category_hint="web")
MOUSE_TOOLS = wrap_all(MOUSE_TOOLS, category_hint="mouse")
FILE_SEARCH_TOOLS = wrap_all(FILE_SEARCH_TOOLS, category_hint="files")
PROCESS_NETWORK_TOOLS = wrap_all(PROCESS_NETWORK_TOOLS, category_hint="process")
SCHEDULER_TOOLS = wrap_all(SCHEDULER_TOOLS, category_hint="schedule")
MEDIA_TOOLS = wrap_all(MEDIA_TOOLS, category_hint="media")
GIT_TOOLS = wrap_all(GIT_TOOLS, category_hint="git")
FILE_TOOLS = wrap_all(FILE_TOOLS, category_hint="code")
DOCUMENT_TOOLS = wrap_all(DOCUMENT_TOOLS, category_hint="docs")
DEV_TOOLS = wrap_all(DEV_TOOLS, category_hint="dev")
BROWSER_TOOLS = wrap_all(BROWSER_TOOLS, category_hint="browser")
CALENDAR_TOOLS = wrap_all(CALENDAR_TOOLS, category_hint="schedule")
CODE_LIBRARY_TOOLS = wrap_all(CODE_LIBRARY_TOOLS, category_hint="code")
EMAIL_TOOLS = wrap_all(EMAIL_TOOLS, category_hint="email")
DATABASE_TOOLS = wrap_all(DATABASE_TOOLS, category_hint="db")
GITHUB_TOOLS = wrap_all(GITHUB_TOOLS, category_hint="github")
API_CLIENT_TOOLS = wrap_all(API_CLIENT_TOOLS, category_hint="api")
SPREADSHEET_TOOLS = wrap_all(SPREADSHEET_TOOLS, category_hint="spreadsheet")
CODEBASE_TOOLS = wrap_all(CODEBASE_TOOLS, category_hint="codebase")
SHELL_TOOLS = wrap_all(SHELL_TOOLS, category_hint="shell")
LEARN_TOPIC_TOOLS = wrap_all(LEARN_TOPIC_TOOLS, category_hint="learn")


CHAT_TOOLS: list[Any] = [*KNOWLEDGE_TOOLS]

CODER_TOOLS: list[Any] = [
    *FILE_TOOLS, *GIT_TOOLS, *FILE_SEARCH_TOOLS,
    *CODE_LIBRARY_TOOLS,
    *CODEBASE_TOOLS,
    *SHELL_TOOLS,
    *LEARN_TOPIC_TOOLS,
    *DEV_TOOLS, web_search, python_exec, calculator,
]

ULTRON_TOOLS: list[Any] = [
    *SYSTEM_TOOLS,
    *COMM_TOOLS,
    *EMAIL_TOOLS,
    *VISION_TOOLS,
    *VISION_LLM_TOOLS,
    *GUI_SMART_TOOLS,
    *WEB_FETCH_TOOLS,
    *MOUSE_TOOLS,
    *FILE_SEARCH_TOOLS,
    *PROCESS_NETWORK_TOOLS,
    *SCHEDULER_TOOLS,
    *CALENDAR_TOOLS,
    *MEDIA_TOOLS,
    *DOCUMENT_TOOLS,
    *BROWSER_TOOLS,
    *CODE_LIBRARY_TOOLS,
    *DATABASE_TOOLS,
    *GITHUB_TOOLS,
    *API_CLIENT_TOOLS,
    *SPREADSHEET_TOOLS,
    *CODEBASE_TOOLS,
    *SHELL_TOOLS,
    *LEARN_TOPIC_TOOLS,
    *KNOWLEDGE_TOOLS,
]

ALL_TOOLS = CHAT_TOOLS
