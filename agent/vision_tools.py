"""Vision: OCR the screen, read text from images, describe what's on screen."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from langchain_core.tools import tool


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


@tool
def read_screen() -> str:
    """OCR the entire screen — return all text visible right now. Useful for 'what does the screen say' or reading errors/messages on screen."""
    if not _have("tesseract"):
        return "[error] tesseract not installed (sudo apt install tesseract-ocr)"
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        path = tmp.name
    try:
        if not _take_screenshot(path):
            return "[error] could not capture screen"
        r = subprocess.run(
            ["tesseract", path, "-", "-l", "eng"],
            capture_output=True, text=True, timeout=30,
        )
        text = r.stdout.strip()
        return text or "(no text detected)"
    finally:
        Path(path).unlink(missing_ok=True)


@tool
def read_image(path: str) -> str:
    """OCR an image file. Returns extracted text."""
    p = Path(path).expanduser()
    if not p.exists():
        return f"[error] {path} not found"
    if not _have("tesseract"):
        return "[error] tesseract not installed"
    try:
        r = subprocess.run(
            ["tesseract", str(p), "-", "-l", "eng"],
            capture_output=True, text=True, timeout=30,
        )
        return r.stdout.strip() or "(no text detected)"
    except Exception as e:
        return f"[error] {e}"


@tool
def find_text_on_screen(text: str) -> str:
    """Check if specific text appears on the screen right now. Returns 'yes' / 'no' + context."""
    full = read_screen.invoke({})
    if full.startswith("[error]"):
        return full
    text_lower = text.lower()
    full_lower = full.lower()
    if text_lower not in full_lower:
        return f"no — '{text}' not on screen"
    idx = full_lower.find(text_lower)
    snippet = full[max(0, idx - 60): idx + 60 + len(text)]
    return f"yes — context: …{snippet}…"


@tool
def describe_screen() -> str:
    """Lightweight description of what's on screen: visible text + active windows. For richer image understanding install a vision model."""
    text = read_screen.invoke({})
    summary_text = (text[:1500] + "…") if len(text) > 1500 else text
    parts = [f"--- screen text ---\n{summary_text}"]

    if _have("wmctrl"):
        try:
            r = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, timeout=5)
            wins = r.stdout.strip().split("\n")[:15]
            parts.append("--- visible windows ---\n" + "\n".join(
                w.split(None, 3)[-1] if len(w.split(None, 3)) > 3 else w
                for w in wins
            ))
        except Exception:
            pass
    return "\n\n".join(parts)


VISION_TOOLS = [read_screen, read_image, find_text_on_screen, describe_screen]
