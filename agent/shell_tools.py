"""Shell execution. Runs any command on the user's own system."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from langchain_core.tools import tool


@tool
def shell_exec(command: str, cwd: str = "", timeout: int = 60) -> str:
    """Run a shell command. Returns stdout + stderr + exit code.
    cwd: working directory (default = home). timeout in seconds (default 60, max 600).

    Examples:
      shell_exec("ls -la /tmp")
      shell_exec("apt list --installed | grep python")
      shell_exec("npm install lodash", cwd="/home/me/project")
      shell_exec("docker ps")
    """
    timeout = max(1, min(int(timeout), 600))
    work = Path(cwd).expanduser() if cwd else Path.home()
    if not work.exists():
        work = Path.home()
    try:
        r = subprocess.run(
            command, shell=True, executable="/bin/bash",
            capture_output=True, text=True,
            timeout=timeout, cwd=str(work),
            env={**os.environ},
        )
    except subprocess.TimeoutExpired:
        return f"[timeout] killed after {timeout}s"
    except Exception as e:
        return f"[error] {e}"

    out = (r.stdout or "")[-6000:]
    err = (r.stderr or "")[-3000:]
    parts = [f"$ {command}"]
    if out:
        parts.append(out)
    if err:
        parts.append(f"--- stderr ---\n{err}")
    parts.append(f"(exit {r.returncode})")
    return "\n".join(parts)


@tool
def shell_pipe(command: str, input_text: str, cwd: str = "", timeout: int = 60) -> str:
    """Run a shell command and pipe input_text to its stdin. Useful for grep, sort, jq, etc."""
    timeout = max(1, min(int(timeout), 600))
    work = Path(cwd).expanduser() if cwd else Path.home()
    if not work.exists():
        work = Path.home()
    try:
        r = subprocess.run(
            command, shell=True, executable="/bin/bash",
            input=input_text, capture_output=True, text=True,
            timeout=timeout, cwd=str(work),
        )
    except subprocess.TimeoutExpired:
        return f"[timeout] killed after {timeout}s"
    except Exception as e:
        return f"[error] {e}"
    return ((r.stdout or "")[-6000:] + (f"\n--- stderr ---\n{r.stderr[-2000:]}" if r.stderr else "")).strip()


@tool
def shell_background(command: str, cwd: str = "") -> str:
    """Start a long-running command in the background. Returns the PID immediately.
    Examples:
      shell_background('python -m http.server 8000', cwd='/tmp')
      shell_background('streamlit run app.py')
    """
    work = Path(cwd).expanduser() if cwd else Path.home()
    if not work.exists():
        work = Path.home()
    try:
        proc = subprocess.Popen(
            command, shell=True, executable="/bin/bash",
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            cwd=str(work), start_new_session=True,
        )
        return f"✓ started pid {proc.pid}: {command}"
    except Exception as e:
        return f"[error] {e}"


@tool
def sudo_exec(command: str, password: str = "") -> str:
    """Run a command with sudo. password: optional, otherwise reads from vault key 'sudo_password'.
    Examples:
      sudo_exec("apt install -y htop")
      sudo_exec("systemctl restart nginx")
    """
    pw = password
    if not pw:
        try:
            from agent.credential_vault import get_credential
            pw = get_credential("sudo_password") or ""
        except Exception:
            pw = ""
    if not pw:
        return "[error] no sudo password provided and 'sudo_password' not in vault"
    try:
        r = subprocess.run(
            f"sudo -S -p '' bash -c {repr(command)}",
            shell=True, executable="/bin/bash",
            input=pw + "\n", capture_output=True, text=True, timeout=120,
        )
    except subprocess.TimeoutExpired:
        return "[timeout]"
    except Exception as e:
        return f"[error] {e}"
    out = (r.stdout or "")[-4000:]
    err = (r.stderr or "")[-2000:]
    return f"$ sudo {command}\n{out}" + (f"\n--- stderr ---\n{err}" if err else "") + f"\n(exit {r.returncode})"


SHELL_TOOLS = [shell_exec, shell_pipe, shell_background, sudo_exec]
