"""Optional: image understanding via local LLaVA / MiniCPM-V (Ollama).

This is heavier than OCR — falls back gracefully if model isn't pulled.
First call: `ollama pull moondream` (1.6 GB) for a small fast vision model."""
from __future__ import annotations

import base64
import shutil
import subprocess
import tempfile
from pathlib import Path

from langchain_core.tools import tool
from langchain_ollama import ChatOllama

from config import LLM_NUM_CTX


VISION_MODEL = "moondream"


def _have(c: str) -> bool:
    return shutil.which(c) is not None


def _take_screenshot(path: str) -> bool:
    for cmd in (
        ["gnome-screenshot", "-f", path],
        ["scrot", path],
        ["import", "-window", "root", path],
        ["grim", path],
    ):
        if _have(cmd[0]):
            try:
                subprocess.run(cmd, capture_output=True, timeout=10)
                if Path(path).exists():
                    return True
            except Exception:
                continue
    return False


def _ask_vision(image_path: str, question: str) -> str:
    try:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
    except Exception as e:
        return f"[error] {e}"

    try:
        llm = ChatOllama(model=VISION_MODEL, num_ctx=LLM_NUM_CTX)
        msg = llm.invoke([{
            "role": "user",
            "content": [
                {"type": "text", "text": question},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ],
        }])
        return msg.content
    except Exception as e:
        return f"[error] vision model not available — `ollama pull {VISION_MODEL}` ({e})"


@tool
def describe_image(path: str, question: str = "What is in this image?") -> str:
    """Use a local vision model (LLaVA/Moondream) to describe an image. Far richer than OCR."""
    p = Path(path).expanduser()
    if not p.exists():
        return f"[error] {path} not found"
    return _ask_vision(str(p), question)


@tool
def describe_screen_visual(question: str = "Describe what's on the screen.") -> str:
    """Capture the screen and ask a vision model about it. Slower but richer than OCR."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        path = tmp.name
    try:
        if not _take_screenshot(path):
            return "[error] could not capture screen"
        return _ask_vision(path, question)
    finally:
        Path(path).unlink(missing_ok=True)


VISION_LLM_TOOLS = [describe_image, describe_screen_visual]
