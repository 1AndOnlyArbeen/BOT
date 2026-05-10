"""Package-management tools — list, install, uninstall, sync.

Wraps cli/packages.py for the langchain agent. The model can ask
naturally ("install fastapi", "what deps do we have?") and we figure out
the right package manager from the detected project profile.
"""
from __future__ import annotations

import subprocess

from langchain_core.tools import tool

from cli import packages as _pkg
from cli.project.detect import project_profile


# 5 minute cap. Installs can take a while on slow networks.
INSTALL_TIMEOUT_SEC = 300


def _run(cmd: str) -> tuple[int, str]:
    """Run a shell command in the workspace root with a hard timeout."""
    profile = project_profile()
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=str(profile.root),
            capture_output=True,
            text=True,
            timeout=INSTALL_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired:
        return 124, f"[timeout after {INSTALL_TIMEOUT_SEC}s] {cmd}"
    except Exception as e:
        return 1, f"[exec error] {e}"
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


@tool("list_dependencies")
def list_dependencies() -> str:
    """List ALL packages declared anywhere in the workspace.

    Reads package.json, pyproject.toml, requirements.txt, environment.yml,
    Cargo.toml, go.mod, composer.json, Gemfile, pubspec.yaml. Use this to
    answer "what packages do we have?", "is X already a dep?", or before
    you propose installing something the user might already have.
    """
    manifests = _pkg.read_dependencies()
    if not manifests:
        return "(no package manifest found in this workspace)"

    out: list[str] = []
    for m in manifests:
        prod = [d for d in m.deps if not d.dev]
        dev = [d for d in m.deps if d.dev]
        out.append(f"### {m.name}  ({len(prod)} deps, {len(dev)} dev)")
        if prod:
            out.append("  deps:")
            for d in prod:
                ver = f"  {d.version}" if d.version else ""
                out.append(f"    - {d.name}{ver}")
        if dev:
            out.append("  dev:")
            for d in dev:
                ver = f"  {d.version}" if d.version else ""
                out.append(f"    - {d.name}{ver}")
        if m.scripts:
            out.append("  scripts:")
            for k, v in m.scripts.items():
                out.append(f"    - {k}: {v}")
        out.append("")
    return "\n".join(out).rstrip()


@tool("install_package")
def install_package(name: str, dev: bool = False) -> str:
    """Install a package using the workspace's auto-detected package manager.

    Picks the right command automatically:
      - npm/pnpm/yarn/bun for JS/TS (--save-dev / -D for dev deps)
      - uv/poetry/pip for Python
      - cargo for Rust, go get for Go

    Pass dev=True for development-only packages. Returns the actual
    command run plus its output. Use list_dependencies first to check
    if the package is already declared.
    """
    profile = project_profile()
    cmd = _pkg.install_command(profile, name, dev=dev)
    if cmd is None:
        return (
            f"[install_package] no package manager detected for "
            f"{profile.root} — declare a manifest first or run shell_exec manually."
        )
    code, out = _run(cmd)
    head = f"$ {cmd}\n"
    body = out or "(no output)"
    suffix = "" if code == 0 else f"\n[exit {code}]"
    return head + body + suffix


@tool("uninstall_package")
def uninstall_package(name: str) -> str:
    """Remove a package with the detected package manager. Returns command + output."""
    profile = project_profile()
    cmd = _pkg.uninstall_command(profile, name)
    if cmd is None:
        return (
            f"[uninstall_package] no package manager detected for {profile.root}."
        )
    code, out = _run(cmd)
    return f"$ {cmd}\n{out or '(no output)'}" + ("" if code == 0 else f"\n[exit {code}]")


@tool("sync_packages")
def sync_packages() -> str:
    """Install ALL packages declared in the workspace's manifest.

    Use after cloning a repo or after pulling new changes. Picks the
    right command:
      - npm install / pnpm install / yarn install / bun install
      - uv sync / poetry install / pip install -r requirements.txt
      - cargo build / go mod download
    """
    profile = project_profile()
    cmd = _pkg.sync_command(profile)
    if cmd is None:
        return f"[sync_packages] no package manager detected for {profile.root}."
    code, out = _run(cmd)
    return f"$ {cmd}\n{out or '(no output)'}" + ("" if code == 0 else f"\n[exit {code}]")
