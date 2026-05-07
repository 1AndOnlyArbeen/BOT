"""System control tools for Linux. Launch apps, screenshot, clipboard, volume, type/click."""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import time
from pathlib import Path

from langchain_core.tools import tool


SCREENSHOT_DIR = Path.home() / "Pictures" / "Ultron"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


APP_ALIASES = {
    "browser": ["xdg-open", "https://duckduckgo.com"],
    "firefox": ["firefox"],
    "chrome": ["google-chrome"],
    "chromium": ["chromium"],
    "vscode": ["code"],
    "code": ["code"],
    "terminal": ["gnome-terminal"],
    "files": ["nautilus"],
    "calculator": ["gnome-calculator"],
    "spotify": ["spotify"],
    "settings": ["gnome-control-center"],
    "screenshot tool": ["gnome-screenshot", "-i"],
}


def _have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _run(args: list[str], detach: bool = True) -> str:
    try:
        if detach:
            subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return f"✓ launched: {' '.join(args)}"
        else:
            r = subprocess.run(args, capture_output=True, text=True, timeout=10)
            out = (r.stdout or "") + (r.stderr or "")
            return out.strip() or f"(exit {r.returncode})"
    except FileNotFoundError:
        return f"[error] command not found: {args[0]}"
    except Exception as e:
        return f"[error] {e}"


@tool
def open_app(name: str) -> str:
    """Open a desktop application by name. Examples: firefox, chrome, vscode, terminal, files, calculator, spotify."""
    name = name.lower().strip()
    args = APP_ALIASES.get(name)
    if not args:
        if _have(name):
            args = [name]
        else:
            return f"[error] unknown app '{name}'. Known: {', '.join(APP_ALIASES)}"
    if not _have(args[0]):
        return f"[error] '{args[0]}' is not installed"
    return _run(args)


@tool
def open_url(url: str) -> str:
    """Open a URL in the default browser."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return _run(["xdg-open", url])


@tool
def screenshot(filename: str = "") -> str:
    """Take a full-screen screenshot. Saved to ~/Pictures/Ultron/. Returns the path."""
    if not filename:
        filename = f"screenshot_{int(time.time())}.png"
    if not filename.endswith(".png"):
        filename += ".png"
    path = SCREENSHOT_DIR / filename

    for tool_cmd in (
        ["gnome-screenshot", "-f", str(path)],
        ["scrot", str(path)],
        ["import", "-window", "root", str(path)],
        ["grim", str(path)],
    ):
        if _have(tool_cmd[0]):
            r = subprocess.run(tool_cmd, capture_output=True, text=True, timeout=10)
            if path.exists():
                return f"✓ saved {path}"
            return f"[error] {r.stderr.strip() or 'failed'}"
    return "[error] no screenshot tool found (install gnome-screenshot or scrot)"


@tool
def clipboard_copy(text: str) -> str:
    """Copy text to the system clipboard."""
    for cmd in (["xclip", "-selection", "clipboard"], ["wl-copy"]):
        if _have(cmd[0]):
            try:
                p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                p.communicate(input=text.encode("utf-8"), timeout=5)
                return f"✓ copied {len(text)} chars"
            except Exception as e:
                return f"[error] {e}"
    return "[error] install xclip or wl-clipboard"


@tool
def clipboard_paste() -> str:
    """Read the current clipboard contents."""
    for cmd in (["xclip", "-selection", "clipboard", "-o"], ["wl-paste"]):
        if _have(cmd[0]):
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                return r.stdout
            except Exception as e:
                return f"[error] {e}"
    return "[error] install xclip or wl-clipboard"


def _is_wayland() -> bool:
    return os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"


@tool
def type_text(text: str) -> str:
    """Type text wherever the cursor currently is. Uses xdotool on X11, ydotool on Wayland."""
    if _is_wayland() and _have("ydotool"):
        try:
            subprocess.run(["ydotool", "type", "--key-delay", "30", text], timeout=15)
            return f"✓ typed {len(text)} chars (wayland)"
        except Exception as e:
            return f"[error] {e}"
    if _have("xdotool"):
        try:
            subprocess.run(["xdotool", "type", "--delay", "30", text], timeout=15)
            return f"✓ typed {len(text)} chars"
        except Exception as e:
            return f"[error] {e}"
    return "[error] install xdotool (X11) or ydotool (Wayland)"


@tool
def press_key(key: str) -> str:
    """Press a keyboard key or chord. Examples: Return, Tab, Escape, ctrl+c, alt+Tab, super."""
    if _is_wayland() and _have("ydotool"):
        try:
            subprocess.run(["ydotool", "key", key], timeout=5)
            return f"✓ pressed {key} (wayland)"
        except Exception as e:
            return f"[error] {e}"
    if _have("xdotool"):
        try:
            subprocess.run(["xdotool", "key", key], timeout=5)
            return f"✓ pressed {key}"
        except Exception as e:
            return f"[error] {e}"
    return "[error] install xdotool (X11) or ydotool (Wayland)"


@tool
def notify(title: str, message: str = "") -> str:
    """Show a desktop notification."""
    if not _have("notify-send"):
        return "[error] notify-send not installed"
    args = ["notify-send", title]
    if message:
        args.append(message)
    return _run(args, detach=False) or "✓ notified"


@tool
def set_volume(percent: int) -> str:
    """Set system volume 0-100."""
    percent = max(0, min(100, int(percent)))
    if _have("pactl"):
        return _run(
            ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{percent}%"],
            detach=False,
        ) or f"✓ volume {percent}%"
    if _have("amixer"):
        return _run(["amixer", "set", "Master", f"{percent}%"], detach=False)
    return "[error] no volume tool"


@tool
def media_control(action: str) -> str:
    """Control media playback. action: play, pause, play-pause, next, previous, stop."""
    if not _have("playerctl"):
        return "[error] playerctl not installed"
    return _run(["playerctl", action], detach=False) or f"✓ {action}"


@tool
def lock_screen() -> str:
    """Lock the screen."""
    for cmd in (["xdg-screensaver", "lock"], ["gnome-screensaver-command", "-l"], ["loginctl", "lock-session"]):
        if _have(cmd[0]):
            return _run(cmd, detach=False) or "✓ locked"
    return "[error] no lock tool"


@tool
def system_info() -> str:
    """Get current system info: time, uptime, memory, disk, battery."""
    parts = []
    parts.append(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        with open("/proc/uptime") as f:
            up = float(f.read().split()[0])
        h, rem = divmod(int(up), 3600)
        m = rem // 60
        parts.append(f"Uptime: {h}h {m}m")
    except Exception:
        pass
    try:
        import shutil as sh
        d = sh.disk_usage("/")
        parts.append(f"Disk /: {d.used // (1024**3)}G used / {d.total // (1024**3)}G")
    except Exception:
        pass
    try:
        with open("/proc/meminfo") as f:
            mem = f.read()
        total = int([l for l in mem.split("\n") if "MemTotal" in l][0].split()[1]) // 1024
        avail = int([l for l in mem.split("\n") if "MemAvailable" in l][0].split()[1]) // 1024
        parts.append(f"RAM: {total - avail}M used / {total}M")
    except Exception:
        pass
    bat = Path("/sys/class/power_supply/BAT0/capacity")
    if bat.exists():
        parts.append(f"Battery: {bat.read_text().strip()}%")
    return "\n".join(parts)


@tool
def list_running_apps() -> str:
    """List currently visible windows (running GUI apps)."""
    if not _have("wmctrl"):
        return "[error] wmctrl not installed"
    r = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True)
    return r.stdout.strip() or "(none)"


@tool
def focus_window(name: str) -> str:
    """Bring a window with matching title to the foreground."""
    if not _have("wmctrl"):
        return "[error] wmctrl not installed"
    r = subprocess.run(["wmctrl", "-a", name], capture_output=True, text=True)
    if r.returncode == 0:
        return f"✓ focused {name}"
    return f"[error] no window matching '{name}'"


SYSTEM_TOOLS = [
    open_app, open_url, screenshot,
    clipboard_copy, clipboard_paste,
    type_text, press_key,
    notify, set_volume, media_control,
    lock_screen, system_info,
    list_running_apps, focus_window,
]
