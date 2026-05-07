"""Smart GUI control: click on screen text via OCR + xdotool, active-window awareness."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from langchain_core.tools import tool


def _have(c: str) -> bool:
    return shutil.which(c) is not None


def _is_wayland() -> bool:
    return os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"


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


def _click_at(x: int, y: int) -> str:
    if _is_wayland() and _have("ydotool"):
        subprocess.run(["ydotool", "mousemove", "--", str(x), str(y)], timeout=5)
        subprocess.run(["ydotool", "click", "0xC0"], timeout=5)
        return "wayland"
    if _have("xdotool"):
        subprocess.run(["xdotool", "mousemove", str(x), str(y), "click", "1"], timeout=5)
        return "x11"
    raise RuntimeError("install xdotool or ydotool")


@tool
def click_text(text: str) -> str:
    """Click on the first occurrence of `text` on the screen. Uses OCR to locate it.

    Examples: click_text("Submit"), click_text("File"), click_text("Save").
    Returns the position clicked or an error."""
    if not _have("tesseract"):
        return "[error] tesseract not installed (sudo apt install tesseract-ocr)"

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        png = tmp.name
    try:
        if not _take_screenshot(png):
            return "[error] screenshot failed"
        r = subprocess.run(
            ["tesseract", png, "-", "-c", "tessedit_create_tsv=1", "tsv"],
            capture_output=True, text=True, timeout=30,
        )
        rows = r.stdout.split("\n")
        if not rows or len(rows) < 2:
            return f"[error] OCR returned no data"
        target = text.lower()
        for line in rows[1:]:
            cols = line.split("\t")
            if len(cols) >= 12 and cols[11].strip():
                word = cols[11].strip()
                if target in word.lower():
                    try:
                        left = int(cols[6]); top = int(cols[7])
                        w = int(cols[8]); h = int(cols[9])
                        cx = left + w // 2
                        cy = top + h // 2
                        backend = _click_at(cx, cy)
                        return f"✓ clicked '{word}' at ({cx},{cy}) via {backend}"
                    except (ValueError, RuntimeError) as e:
                        return f"[error] {e}"
        return f"[not found] '{text}' is not visible on screen"
    finally:
        Path(png).unlink(missing_ok=True)


@tool
def active_window() -> str:
    """Get the currently focused window: title, app name, PID, geometry."""
    if _have("xdotool"):
        try:
            wid = subprocess.run(
                ["xdotool", "getactivewindow"], capture_output=True, text=True, timeout=5,
            ).stdout.strip()
            if not wid:
                return "(no active window)"
            name = subprocess.run(
                ["xdotool", "getwindowname", wid], capture_output=True, text=True, timeout=5,
            ).stdout.strip()
            pid = subprocess.run(
                ["xdotool", "getwindowpid", wid], capture_output=True, text=True, timeout=5,
            ).stdout.strip()
            geom = subprocess.run(
                ["xdotool", "getwindowgeometry", wid], capture_output=True, text=True, timeout=5,
            ).stdout.strip()
            return f"window: {name}\npid: {pid}\n{geom}"
        except Exception as e:
            return f"[error] {e}"
    return "[error] xdotool not available"


@tool
def active_window_text() -> str:
    """OCR just the active window (not the whole screen). Returns visible text."""
    if not _have("xdotool") or not _have("tesseract"):
        return "[error] need xdotool + tesseract"
    try:
        wid = subprocess.run(
            ["xdotool", "getactivewindow"], capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        if not wid:
            return "(no active window)"
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            path = tmp.name
        try:
            r = subprocess.run(
                ["import", "-window", wid, path],
                capture_output=True, timeout=15,
            )
            if not Path(path).exists():
                if _have("gnome-screenshot"):
                    subprocess.run(["gnome-screenshot", "-w", "-f", path], timeout=15)
            if not Path(path).exists():
                return "[error] could not capture window"
            r = subprocess.run(
                ["tesseract", path, "-", "-l", "eng"],
                capture_output=True, text=True, timeout=30,
            )
            return r.stdout.strip() or "(no text)"
        finally:
            Path(path).unlink(missing_ok=True)
    except Exception as e:
        return f"[error] {e}"


@tool
def list_visible_text() -> str:
    """List all words currently visible on screen (deduped, useful for 'what's clickable')."""
    if not _have("tesseract"):
        return "[error] tesseract not installed"
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        png = tmp.name
    try:
        if not _take_screenshot(png):
            return "[error] screenshot failed"
        r = subprocess.run(
            ["tesseract", png, "-", "-l", "eng"],
            capture_output=True, text=True, timeout=30,
        )
        words = []
        for line in r.stdout.split("\n"):
            for w in line.split():
                w = w.strip(".,;:!?()[]{}\"'")
                if 2 <= len(w) <= 30 and any(c.isalpha() for c in w):
                    words.append(w)
        seen = []
        out = []
        for w in words:
            if w.lower() not in seen:
                seen.append(w.lower())
                out.append(w)
            if len(out) >= 40:
                break
        return ", ".join(out) or "(no text)"
    finally:
        Path(png).unlink(missing_ok=True)


GUI_SMART_TOOLS = [click_text, active_window, active_window_text, list_visible_text]
