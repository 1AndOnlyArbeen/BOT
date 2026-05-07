"""Ultron CLI — terminal access to the same agent the web UI uses.

Modes:
- direct (default): calls agent.graph directly. No backend needed.
  Same SQLite, same RAG store, same memory as the web UI — sessions are shared.
- remote (--remote): talks to a running backend over /api/chat/stream SSE.

Entry point: `python -m agent.cli` or the wrapper script `./ultron`.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Iterable, Iterator

from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.panel import Panel
from rich.text import Text


HELP = """\
Slash commands (REPL):
  /mode <chat|coder|ultron>   Switch agent mode
  /planner <on|off>           Toggle plan-then-execute (ultron only)
  /new [title]                Start a new session
  /list                       List recent sessions
  /open <id>                  Resume a session by id
  /sessions                   Alias for /list
  /clear                      Clear the screen
  /info                       Show current state
  /help                       Show this help
  /exit, /quit, Ctrl-D        Quit
"""


# ───────────────────────────────────── direct mode ─────────────────────────────────────
def _direct_imports():
    from agent.graph import stream_agent, run_agent
    from agent.memory import (
        new_session, list_sessions, get_messages, add_message,
        rename_session, get_session_mode,
    )
    return {
        "stream_agent": stream_agent,
        "run_agent": run_agent,
        "new_session": new_session,
        "list_sessions": list_sessions,
        "get_messages": get_messages,
        "add_message": add_message,
        "rename_session": rename_session,
        "get_session_mode": get_session_mode,
    }


def stream_direct(message: str, history: list[dict], mode: str, use_planner: bool, api) -> Iterator[dict]:
    if mode == "ultron" and use_planner:
        from agent.planner import make_plan, execute_plan
        plan = make_plan(message)
        yield {"type": "plan", "data": {
            "request": plan.request,
            "steps": [{"index": s.index, "goal": s.goal} for s in plan.steps],
        }}
        for ev in execute_plan(plan, history=history):
            yield ev
        return

    yield from api["stream_agent"](message, history=history, mode=mode)


# ───────────────────────────────────── remote mode ─────────────────────────────────────
def stream_remote(message: str, session_id: int, mode: str, use_planner: bool, base_url: str) -> Iterator[dict]:
    import urllib.request
    body = json.dumps({
        "session_id": session_id, "message": message,
        "mode": mode, "use_planner": use_planner,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/api/chat/stream",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        buf = b""
        for chunk in r:
            buf += chunk
            while b"\n\n" in buf:
                raw, buf = buf.split(b"\n\n", 1)
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data: "):
                    continue
                try:
                    yield json.loads(line[6:])
                except json.JSONDecodeError:
                    continue


def remote_list_sessions(base_url: str, mode: str | None = None) -> list[dict]:
    import urllib.request
    url = f"{base_url}/api/chat/sessions"
    if mode:
        url += f"?mode={mode}"
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.load(r)


def remote_new_session(base_url: str, title: str, mode: str) -> int:
    import urllib.request
    body = json.dumps({"title": title, "mode": mode}).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/api/chat/sessions", data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)["id"]


def remote_get_messages(base_url: str, session_id: int) -> list[dict]:
    import urllib.request
    with urllib.request.urlopen(f"{base_url}/api/chat/sessions/{session_id}/messages", timeout=10) as r:
        return json.load(r)


# ───────────────────────────────────── ui ─────────────────────────────────────
class CLI:
    def __init__(self, mode: str, use_planner: bool, remote: str | None, session_id: int | None) -> None:
        self.console = Console()
        self.mode = mode
        self.use_planner = use_planner
        self.remote = remote
        self.session_id = session_id
        self.api = None if remote else _direct_imports()
        self._ensure_session()

    # -- session management --
    def _list_sessions(self) -> list[dict]:
        if self.remote:
            return remote_list_sessions(self.remote, mode=self.mode)
        return self.api["list_sessions"](mode=self.mode)

    def _new_session(self, title: str = "CLI session") -> int:
        if self.remote:
            return remote_new_session(self.remote, title, self.mode)
        return self.api["new_session"](title, mode=self.mode)

    def _get_messages(self, sid: int) -> list[dict]:
        if self.remote:
            return remote_get_messages(self.remote, sid)
        return self.api["get_messages"](sid)

    def _ensure_session(self) -> None:
        if self.session_id is not None:
            return
        existing = self._list_sessions()
        if existing:
            self.session_id = existing[0]["id"]
        else:
            self.session_id = self._new_session()

    # -- ui helpers --
    def banner(self) -> None:
        target = self.remote or "direct"
        self.console.print(Panel.fit(
            f"[bold cyan]ULTRON[/bold cyan] CLI · mode=[yellow]{self.mode}[/yellow] · "
            f"session=[green]{self.session_id}[/green] · {target}\n"
            f"[dim]/help for commands · Ctrl-D to quit[/dim]",
            border_style="cyan",
        ))

    def info(self) -> None:
        self.console.print(
            f"[cyan]mode:[/cyan] {self.mode}  "
            f"[cyan]planner:[/cyan] {self.use_planner}  "
            f"[cyan]session:[/cyan] {self.session_id}  "
            f"[cyan]target:[/cyan] {self.remote or 'direct'}"
        )

    # -- main turn --
    def turn(self, message: str) -> None:
        history = self._history_for_direct()
        if not self.remote:
            # Mirror what the web backend does so the user message is persisted.
            self.api["add_message"](self.session_id, "user", message)
            if not self.api["get_messages"](self.session_id)[:-1]:
                self.api["rename_session"](self.session_id, _auto_title(message))

        events = (
            stream_remote(message, self.session_id, self.mode, self.use_planner, self.remote)
            if self.remote
            else stream_direct(message, history, self.mode, self.use_planner, self.api)
        )
        final = self._render_stream(events)

        if not self.remote and final and not final.startswith("⚠"):
            try:
                self.api["add_message"](self.session_id, "assistant", final)
            except Exception:
                pass

    def _history_for_direct(self) -> list[dict]:
        if self.remote:
            return []
        msgs = self.api["get_messages"](self.session_id)
        # Drop the message we're about to add (the user's current turn) — added in turn().
        return msgs

    def _render_stream(self, events: Iterable[dict]) -> str:
        final = ""
        live_text = ""
        plan_steps: list[dict] = []
        with Live("", console=self.console, refresh_per_second=12, vertical_overflow="visible") as live:
            for ev in events:
                t = ev.get("type")
                d = ev.get("data")
                if t == "router":
                    cats = ", ".join(d.get("categories", [])) or "default"
                    self.console.print(f"[dim]🧭 {cats} · {d.get('tool_count', 0)} tools[/dim]")
                elif t == "plan":
                    plan_steps = d.get("steps", [])
                    self.console.print("[bold yellow]Plan:[/bold yellow]")
                    for s in plan_steps:
                        self.console.print(f"  [dim]{s['index']}.[/dim] {s.get('goal','')}")
                elif t == "step_start":
                    self.console.print(f"[dim]→ step {d.get('index')}: {d.get('goal','')}[/dim]")
                elif t == "step_end":
                    status = d.get("status", "ok")
                    color = "green" if status == "ok" else "red"
                    self.console.print(f"  [{color}]·[/{color}] {str(d.get('result',''))[:200]}")
                elif t == "tool_call":
                    self.console.print(f"[magenta]🔧 {d.get('name','?')}[/magenta] [dim]{str(d.get('args',''))[:120]}[/dim]")
                elif t == "tool_result":
                    snippet = str(d.get("content", ""))[:200].replace("\n", " ")
                    self.console.print(f"   [dim]↳ {snippet}[/dim]")
                elif t == "token":
                    live_text = d if isinstance(d, str) else str(d)
                    final = live_text
                    live.update(Markdown(live_text))
                elif t == "final":
                    final = d if isinstance(d, str) else str(d)
                    live.update(Markdown(final))
                elif t == "plan_done":
                    summary = (d or {}).get("summary") or final
                    final = summary
                    live.update(Markdown(summary))
                elif t == "error":
                    self.console.print(f"[red]⚠ {d}[/red]")
                    final = f"⚠️ {d}"
        return final

    # -- slash commands --
    def slash(self, line: str) -> bool:
        """Returns False to exit, True to continue."""
        parts = line.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        if cmd in ("/exit", "/quit", "/q"):
            return False
        if cmd == "/help":
            self.console.print(HELP)
        elif cmd == "/info":
            self.info()
        elif cmd == "/clear":
            os.system("clear")
            self.banner()
        elif cmd == "/mode":
            if arg in ("chat", "coder", "ultron"):
                self.mode = arg
                self.session_id = None
                self._ensure_session()
                self.console.print(f"[green]→ mode = {self.mode}, session = {self.session_id}[/green]")
            else:
                self.console.print("[red]usage: /mode <chat|coder|ultron>[/red]")
        elif cmd == "/planner":
            if arg in ("on", "off"):
                self.use_planner = (arg == "on")
                self.console.print(f"[green]→ planner = {self.use_planner}[/green]")
            else:
                self.console.print("[red]usage: /planner <on|off>[/red]")
        elif cmd == "/new":
            title = arg or "CLI session"
            self.session_id = self._new_session(title)
            self.console.print(f"[green]→ new session {self.session_id}: {title}[/green]")
        elif cmd in ("/list", "/sessions"):
            sessions = self._list_sessions()[:20]
            if not sessions:
                self.console.print("[dim](no sessions in this mode)[/dim]")
            for s in sessions:
                marker = "▸" if s["id"] == self.session_id else " "
                self.console.print(f" {marker} [green]{s['id']:>4}[/green]  {s['title']}")
        elif cmd == "/open":
            try:
                sid = int(arg)
            except ValueError:
                self.console.print("[red]usage: /open <id>[/red]")
                return True
            self.session_id = sid
            self.console.print(f"[green]→ session = {sid}[/green]")
        else:
            self.console.print(f"[red]unknown command: {cmd}[/red] — try /help")
        return True

    # -- repl loop --
    def repl(self) -> None:
        self.banner()
        while True:
            try:
                line = self.console.input(f"[bold cyan]{self.mode}[/bold cyan][dim]›[/dim] ")
            except (EOFError, KeyboardInterrupt):
                self.console.print("\n[dim]bye[/dim]")
                return
            line = line.strip()
            if not line:
                continue
            if line.startswith("/"):
                if not self.slash(line):
                    return
                continue
            try:
                self.turn(line)
            except KeyboardInterrupt:
                self.console.print("\n[yellow](interrupted)[/yellow]")
            except Exception as e:
                self.console.print(f"[red]error:[/red] {e}")


def _auto_title(text: str) -> str:
    t = text.strip().split("\n")[0]
    return (t[:40] + "…") if len(t) > 40 else t


# ───────────────────────────────────── arg parsing ─────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ultron",
        description="Ultron CLI — terminal access to your local AI agent.",
        epilog="Examples:\n"
               "  ultron                          # interactive REPL (coder mode)\n"
               "  ultron \"open postman\"         # one-shot, then exit\n"
               "  ultron -m ultron \"screenshot\" # one-shot in ultron mode\n"
               "  ultron --remote http://localhost:8000",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("prompt", nargs="*", help="Prompt to run (omit for interactive REPL)")
    parser.add_argument("-m", "--mode", choices=["chat", "coder", "ultron"], default="coder",
                        help="Agent mode (default: coder)")
    parser.add_argument("-s", "--session", type=int, help="Resume an existing session by id")
    parser.add_argument("--no-planner", action="store_true", help="Disable plan-then-execute (ultron mode)")
    parser.add_argument("--remote", metavar="URL",
                        help="Talk to a running backend instead of calling the agent in-process")
    args = parser.parse_args(argv)

    cli = CLI(
        mode=args.mode,
        use_planner=not args.no_planner,
        remote=args.remote.rstrip("/") if args.remote else None,
        session_id=args.session,
    )

    if args.prompt:
        cli.turn(" ".join(args.prompt))
        return 0

    cli.repl()
    return 0


if __name__ == "__main__":
    sys.exit(main())
