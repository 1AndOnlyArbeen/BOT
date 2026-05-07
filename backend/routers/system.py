"""System info + tool catalogue."""
from __future__ import annotations

from fastapi import APIRouter

from agent.tools import CHAT_TOOLS, CODER_TOOLS, ULTRON_TOOLS
from agent.permissions import tier_of

router = APIRouter()


def _summarize(tools) -> list[dict]:
    out = []
    for t in tools:
        name = getattr(t, "name", str(t))
        desc = getattr(t, "description", "") or ""
        out.append({
            "name": name,
            "description": desc.strip().split("\n")[0][:160],
            "tier": tier_of(name),
        })
    return out


@router.get("/tools")
def tools() -> dict:
    return {
        "chat": _summarize(CHAT_TOOLS),
        "coder": _summarize(CODER_TOOLS),
        "ultron": _summarize(ULTRON_TOOLS),
    }


@router.get("/info")
def info() -> dict:
    import os, platform, shutil
    return {
        "os": platform.system(),
        "kernel": platform.release(),
        "session": os.environ.get("XDG_SESSION_TYPE", "unknown"),
        "ollama_installed": bool(shutil.which("ollama")),
        "tesseract_installed": bool(shutil.which("tesseract")),
        "xdotool_installed": bool(shutil.which("xdotool")),
        "ydotool_installed": bool(shutil.which("ydotool")),
    }
