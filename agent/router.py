"""Intent router: keyword-first, LLM-fallback. Picks the minimal tool subset for a query.

Why: Small models choke on 70-tool prompts. Routing first → only relevant 5-15 tools → far better tool selection."""
from __future__ import annotations

import re
from functools import lru_cache

from langchain_ollama import ChatOllama

from config import LLM_MODEL


CATEGORIES = {
    "system": ["open", "launch", "close", "kill", "screenshot", "volume", "brightness",
               "lock", "screen", "clipboard", "notify", "media", "play", "pause", "spotify"],
    "mouse": ["click", "type", "mouse", "scroll", "drag", "press key", "tab"],
    "vision": ["read screen", "what's on", "see ", "describe screen", "ocr", "image"],
    "comm": ["whatsapp", "telegram", "email", "sms", "message ", "tweet",
             "facebook", "instagram", "linkedin", "messenger", "compose"],
    "search": ["google", "search", "youtube", "duckduckgo", "ddg", "find online", "look up"],
    "web": ["fetch", "scrape", "download", "url", "website", "page content", "public ip"],
    "files": ["find file", "search file", "grep", "recent file", "list dir", "list folder"],
    "process": ["process", "running", "kill", "ping", "network", "wifi", "port", "disk"],
    "schedule": ["remind", "reminder", "schedule", "alarm", "in 5 min", "tomorrow"],
    "media": ["youtube download", "yt-dlp", "record audio", "mp3", "video"],
    "git": ["git ", "commit", "branch", "checkout", "diff", "pull request"],
    "code": ["read file", "write file", "edit file", "run python", "function ",
             "refactor", "implement", "fix bug", "create script",
             "save this as", "save it as", "save that as", "save as",
             "recall ", "pull up the", "give me the", "show me the",
             "list artifacts", "what did i save"],
    "docs": ["pdf", "markdown", "html", "document", "report"],
    "dev": ["pip", "apt", "package", "install", "format", "black", "env"],
    "knowledge": ["my doc", "uploaded", "rag", "explain", "what is", "how does",
                  "calculate", "math", "python code"],
    "browser": ["fill form", "log in to", "login to", "submit form", "click button",
                "browser", "navigate to", "browse"],
    "vision_llm": ["describe image", "what's in this picture", "what's in the image",
                   "look at", "see this image"],
    "email": ["inbox", "email", "mail ", "smtp", "imap", "send mail", "compose mail",
              "@gmail", "reply to", "unread"],
    "db": ["sql", "query", "select ", "table", "database", "postgres", "mysql", "sqlite"],
    "github": ["github", "pull request", "pr ", "issue", "repo ", "gh "],
    "api": ["http get", "http post", "rest api", "graphql", "endpoint", "curl"],
    "spreadsheet": ["csv", "xlsx", "excel", "spreadsheet", "pandas", "dataframe"],
    "codebase": ["how do i", "how can i", "how to create", "where is", "find function",
                 "in this codebase", "in the project", "show me the code",
                 "explain the", "trace the", "what does this code", "where in the code"],
    "shell": ["run ", "execute ", "shell ", "bash ", "command ", "cmd ", "terminal ",
              "sudo ", "apt ", "systemctl", "docker ", "kubectl", "pip install",
              "npm install", "git clone", "curl ", "wget "],
}


KEYWORD_FAST_PATH_THRESHOLD = 1


def _keyword_route(query: str) -> set[str]:
    """Pure keyword scoring — instant, no LLM call."""
    q = query.lower()
    scores: dict[str, int] = {}
    for cat, kws in CATEGORIES.items():
        score = sum(1 for kw in kws if kw in q)
        if score:
            scores[cat] = score
    if not scores:
        return set()
    top = max(scores.values())
    return {cat for cat, sc in scores.items() if sc >= max(1, top - 1)}


@lru_cache(maxsize=1)
def _llm():
    return ChatOllama(model=LLM_MODEL, temperature=0.0, num_predict=80)


CLASSIFY_PROMPT = """Classify the user request into 1-3 of these categories. Return ONLY the category names, comma-separated.

CATEGORIES:
- system: open apps, screenshot, volume, brightness, clipboard, notify, media playback, lock, system info
- mouse: click, type at cursor, scroll, drag, key press
- vision: read what's on screen, OCR, describe screen, read image
- comm: WhatsApp, Telegram, email, SMS, social messaging
- search: web search (Google, YouTube, DuckDuckGo)
- web: fetch URL content, scrape, download file
- files: find files, grep contents, list directories on disk
- process: running processes, kill, ping, network, wifi, ports, disk
- schedule: reminders, alarms, scheduling
- media: download YouTube, record audio
- git: git operations
- code: read/write/edit code, run scripts, debug, refactor
- docs: generate PDFs, markdown, HTML
- dev: pip/apt search, format code, env info
- knowledge: ask about uploaded documents, calculations, general Q&A

User request: {query}

Categories:"""


def llm_route(query: str) -> set[str]:
    try:
        resp = _llm().invoke(CLASSIFY_PROMPT.format(query=query)).content
    except Exception:
        return set()
    resp = re.sub(r"<think>.*?</think>", "", resp, flags=re.DOTALL)
    found = set()
    lower = resp.lower()
    for cat in CATEGORIES:
        if cat in lower:
            found.add(cat)
    return found


def route(query: str) -> set[str]:
    """Return categories of tools the agent likely needs."""
    kw = _keyword_route(query)
    if len(kw) >= KEYWORD_FAST_PATH_THRESHOLD:
        return kw
    llm = llm_route(query)
    return llm or {"knowledge", "system"}


def tools_for_categories(cats: set[str]) -> list:
    """Map categories → concrete tool list. Keeps the prompt small."""
    from agent.system_tools import SYSTEM_TOOLS
    from agent.mouse_tools import MOUSE_TOOLS
    from agent.vision_tools import VISION_TOOLS
    from agent.comm_tools import COMM_TOOLS
    from agent.web_tools import WEB_FETCH_TOOLS
    from agent.file_search import FILE_SEARCH_TOOLS
    from agent.process_tools import PROCESS_NETWORK_TOOLS
    from agent.scheduler import SCHEDULER_TOOLS
    from agent.media_tools import MEDIA_TOOLS
    from agent.git_tools import GIT_TOOLS
    from agent.file_tools import FILE_TOOLS
    from agent.document_tools import DOCUMENT_TOOLS
    from agent.dev_tools import DEV_TOOLS
    from agent.tools import KNOWLEDGE_TOOLS, web_search, ARTIFACT_TOOLS

    bundle: list = []
    if "system" in cats: bundle += SYSTEM_TOOLS
    if "mouse" in cats: bundle += MOUSE_TOOLS
    if "vision" in cats: bundle += VISION_TOOLS
    if "comm" in cats: bundle += COMM_TOOLS
    if "search" in cats: bundle += [web_search] + COMM_TOOLS[4:7]
    if "web" in cats: bundle += WEB_FETCH_TOOLS
    if "files" in cats: bundle += FILE_SEARCH_TOOLS
    if "process" in cats: bundle += PROCESS_NETWORK_TOOLS
    if "schedule" in cats: bundle += SCHEDULER_TOOLS
    if "media" in cats: bundle += MEDIA_TOOLS
    if "git" in cats: bundle += GIT_TOOLS
    if "code" in cats: bundle += FILE_TOOLS + ARTIFACT_TOOLS + DEV_TOOLS
    if "docs" in cats: bundle += DOCUMENT_TOOLS
    if "dev" in cats: bundle += DEV_TOOLS
    if "knowledge" in cats: bundle += KNOWLEDGE_TOOLS
    if "browser" in cats:
        from agent.browser_automation import BROWSER_TOOLS
        bundle += BROWSER_TOOLS
    if "vision_llm" in cats:
        from agent.vision_llm import VISION_LLM_TOOLS
        bundle += VISION_LLM_TOOLS
    if "email" in cats:
        from agent.email_tools import EMAIL_TOOLS
        bundle += EMAIL_TOOLS
    if "db" in cats:
        from agent.database_tools import DATABASE_TOOLS
        bundle += DATABASE_TOOLS
    if "github" in cats:
        from agent.github_tools import GITHUB_TOOLS
        bundle += GITHUB_TOOLS
    if "api" in cats:
        from agent.api_client import API_CLIENT_TOOLS
        bundle += API_CLIENT_TOOLS
    if "spreadsheet" in cats:
        from agent.spreadsheet_tools import SPREADSHEET_TOOLS
        bundle += SPREADSHEET_TOOLS
    if "codebase" in cats:
        from agent.codebase_tools import CODEBASE_TOOLS
        bundle += CODEBASE_TOOLS
    if "shell" in cats:
        from agent.shell_tools import SHELL_TOOLS
        bundle += SHELL_TOOLS

    if not bundle:
        bundle = list(KNOWLEDGE_TOOLS)

    seen = set()
    out = []
    for t in bundle:
        n = getattr(t, "name", None) or str(t)
        if n in seen:
            continue
        seen.add(n)
        out.append(t)

    try:
        from agent.tool_learning import rank_tools
        out = rank_tools(out, cats)
    except Exception:
        pass

    return out[:20]
