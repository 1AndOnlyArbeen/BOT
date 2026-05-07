"""Mouse + advanced input + brightness + display info."""
from __future__ import annotations

import shutil
import subprocess

from langchain_core.tools import tool


def _have(c: str) -> bool:
    return shutil.which(c) is not None


@tool
def mouse_position() -> str:
    """Get current mouse cursor position (x, y)."""
    if not _have("xdotool"):
        return "[error] xdotool not installed"
    r = subprocess.run(
        ["xdotool", "getmouselocation", "--shell"],
        capture_output=True, text=True, timeout=5,
    )
    return r.stdout.strip()


@tool
def mouse_move(x: int, y: int) -> str:
    """Move mouse to absolute screen coordinates (x, y)."""
    if not _have("xdotool"):
        return "[error] xdotool not installed"
    subprocess.run(["xdotool", "mousemove", str(x), str(y)], timeout=5)
    return f"✓ moved to ({x}, {y})"


@tool
def mouse_click(button: str = "left") -> str:
    """Click the mouse. button: left, right, middle."""
    if not _have("xdotool"):
        return "[error] xdotool not installed"
    btn = {"left": "1", "middle": "2", "right": "3"}.get(button.lower(), "1")
    subprocess.run(["xdotool", "click", btn], timeout=5)
    return f"✓ {button} click"


@tool
def mouse_double_click(button: str = "left") -> str:
    """Double click."""
    if not _have("xdotool"):
        return "[error] xdotool not installed"
    btn = {"left": "1", "middle": "2", "right": "3"}.get(button.lower(), "1")
    subprocess.run(["xdotool", "click", "--repeat", "2", btn], timeout=5)
    return f"✓ double {button} click"


@tool
def mouse_drag(from_x: int, from_y: int, to_x: int, to_y: int) -> str:
    """Drag mouse from one position to another (left-button hold)."""
    if not _have("xdotool"):
        return "[error] xdotool not installed"
    subprocess.run([
        "xdotool",
        "mousemove", str(from_x), str(from_y),
        "mousedown", "1",
        "mousemove", str(to_x), str(to_y),
        "mouseup", "1",
    ], timeout=10)
    return f"✓ dragged ({from_x},{from_y}) → ({to_x},{to_y})"


@tool
def scroll(direction: str = "down", amount: int = 3) -> str:
    """Scroll the wheel. direction: up or down. amount: scroll ticks."""
    if not _have("xdotool"):
        return "[error] xdotool not installed"
    btn = "5" if direction.lower() == "down" else "4"
    subprocess.run(["xdotool", "click", "--repeat", str(amount), btn], timeout=5)
    return f"✓ scrolled {direction} ×{amount}"


@tool
def get_screen_size() -> str:
    """Get screen resolution."""
    if _have("xdotool"):
        r = subprocess.run(
            ["xdotool", "getdisplaygeometry"],
            capture_output=True, text=True, timeout=5,
        )
        return f"{r.stdout.strip()}"
    if _have("xrandr"):
        r = subprocess.run(["xrandr"], capture_output=True, text=True, timeout=5)
        for line in r.stdout.split("\n"):
            if " connected " in line and "primary" in line:
                return line.split()[3].split("+")[0]
    return "[error] no display tool"


@tool
def set_brightness(percent: int) -> str:
    """Set screen brightness 0-100 (laptop displays only)."""
    percent = max(5, min(100, int(percent)))
    if _have("brightnessctl"):
        subprocess.run(["brightnessctl", "set", f"{percent}%"], timeout=5)
        return f"✓ brightness {percent}%"
    if _have("xbacklight"):
        subprocess.run(["xbacklight", "-set", str(percent)], timeout=5)
        return f"✓ brightness {percent}%"
    return "[error] install brightnessctl or xbacklight"


@tool
def get_brightness() -> str:
    """Get current screen brightness."""
    if _have("brightnessctl"):
        r = subprocess.run(["brightnessctl", "g"], capture_output=True, text=True, timeout=5)
        rmax = subprocess.run(["brightnessctl", "m"], capture_output=True, text=True, timeout=5)
        try:
            cur, mx = int(r.stdout), int(rmax.stdout)
            return f"{round(cur / mx * 100)}%"
        except ValueError:
            pass
    if _have("xbacklight"):
        r = subprocess.run(["xbacklight"], capture_output=True, text=True, timeout=5)
        return f"{r.stdout.strip()}%"
    return "[error] no brightness tool"


MOUSE_TOOLS = [
    mouse_position, mouse_move, mouse_click, mouse_double_click,
    mouse_drag, scroll, get_screen_size,
    set_brightness, get_brightness,
]
