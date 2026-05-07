"""Process and network tools."""
from __future__ import annotations

import os
import shutil
import signal
import subprocess

from langchain_core.tools import tool


def _have(c: str) -> bool:
    return shutil.which(c) is not None


@tool
def list_processes(filter: str = "") -> str:
    """List running processes. filter: optional substring to match command names."""
    r = subprocess.run(
        ["ps", "axo", "pid,pcpu,pmem,comm"],
        capture_output=True, text=True, timeout=10,
    )
    lines = r.stdout.split("\n")
    if filter:
        lines = [lines[0]] + [l for l in lines[1:] if filter.lower() in l.lower()]
    rows = lines[:25]
    return "\n".join(rows) or "(none)"


@tool
def kill_process(pid_or_name: str) -> str:
    """Kill a process by PID or name. Use carefully."""
    arg = pid_or_name.strip()
    try:
        if arg.isdigit():
            os.kill(int(arg), signal.SIGTERM)
            return f"✓ killed pid {arg}"
        if _have("pkill"):
            r = subprocess.run(["pkill", "-f", arg], capture_output=True, text=True, timeout=5)
            return f"✓ killed processes matching '{arg}'" if r.returncode == 0 else f"no match for '{arg}'"
        return "[error] pkill not available"
    except ProcessLookupError:
        return f"[error] no process with pid {arg}"
    except PermissionError:
        return "[error] permission denied (try sudo)"
    except Exception as e:
        return f"[error] {e}"


@tool
def top_processes() -> str:
    """Show top CPU + memory consumers."""
    r = subprocess.run(
        ["ps", "axo", "pid,pcpu,pmem,comm", "--sort=-pcpu"],
        capture_output=True, text=True, timeout=10,
    )
    lines = r.stdout.split("\n")[:11]
    return "\n".join(lines)


@tool
def ping_host(host: str, count: int = 3) -> str:
    """Ping a host (default 3 packets)."""
    if not _have("ping"):
        return "[error] ping unavailable"
    try:
        r = subprocess.run(
            ["ping", "-c", str(count), "-W", "3", host],
            capture_output=True, text=True, timeout=20,
        )
        return r.stdout or r.stderr
    except Exception as e:
        return f"[error] {e}"


@tool
def network_info() -> str:
    """Show local network interfaces and IPs."""
    if _have("ip"):
        r = subprocess.run(["ip", "-br", "addr"], capture_output=True, text=True, timeout=5)
        return r.stdout.strip()
    r = subprocess.run(["ifconfig"], capture_output=True, text=True, timeout=5)
    return r.stdout[:1500]


@tool
def wifi_info() -> str:
    """Get current WiFi connection info."""
    if _have("nmcli"):
        r = subprocess.run(
            ["nmcli", "-t", "-f", "active,ssid,signal,security", "device", "wifi"],
            capture_output=True, text=True, timeout=5,
        )
        active = [l for l in r.stdout.split("\n") if l.startswith("yes:")]
        return active[0] if active else "(not connected)"
    if _have("iwgetid"):
        r = subprocess.run(["iwgetid"], capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or "(no wifi)"
    return "[error] install network-manager"


@tool
def list_open_ports() -> str:
    """Show TCP ports currently listening on this machine."""
    if _have("ss"):
        r = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True, timeout=5)
        return r.stdout[:2000]
    if _have("netstat"):
        r = subprocess.run(["netstat", "-tlnp"], capture_output=True, text=True, timeout=5)
        return r.stdout[:2000]
    return "[error] ss/netstat not available"


@tool
def disk_usage(path: str = "/") -> str:
    """Disk usage for a mount point."""
    r = subprocess.run(["df", "-h", path], capture_output=True, text=True, timeout=5)
    return r.stdout


PROCESS_NETWORK_TOOLS = [
    list_processes, kill_process, top_processes,
    ping_host, network_info, wifi_info, list_open_ports, disk_usage,
]
