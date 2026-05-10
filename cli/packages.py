"""Package-manifest understanding + install dispatch.

Two concerns, kept together because they share the same manifest parsers:

  1. READ — `read_dependencies(root)` returns a structured snapshot of
     every dependency declared anywhere in the workspace. Backs the
     `list_dependencies` tool and the dependency block in the primer.

  2. WRITE — `install_command(profile, name, dev)` and
     `sync_command(profile)` figure out the right shell command for the
     detected package manager, so the model never has to remember
     `pnpm add` vs `npm install` vs `uv add`.

Pure functions where possible. The only side effects live in the tool
layer (cli/tools/packages.py).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from cli.project.detect import ProjectProfile, project_profile


# --- Data shape ------------------------------------------------------------

@dataclass(frozen=True)
class Dependency:
    name: str
    version: str = ""           # raw version spec, "" if unspecified
    dev: bool = False           # devDependency / extras-style dev
    source: str = ""            # which manifest declared it


@dataclass
class Manifest:
    name: str                   # e.g. "package.json"
    deps: list[Dependency] = field(default_factory=list)
    scripts: dict[str, str] = field(default_factory=dict)


# --- Manifest parsers ------------------------------------------------------
#
# Each parser is forgiving — a malformed manifest must NOT crash the CLI.
# Best-effort parsing, return whatever we can read.

def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return None


def _parse_package_json(root: Path) -> Manifest | None:
    p = root / "package.json"
    if not p.exists():
        return None
    text = _read_text(p)
    if not text:
        return None
    try:
        data = json.loads(text)
    except Exception:
        return Manifest(name="package.json")

    m = Manifest(name="package.json")
    for d in (data.get("dependencies") or {}).items():
        m.deps.append(Dependency(name=d[0], version=str(d[1] or ""), dev=False, source="package.json"))
    for d in (data.get("devDependencies") or {}).items():
        m.deps.append(Dependency(name=d[0], version=str(d[1] or ""), dev=True, source="package.json"))
    scripts = data.get("scripts")
    if isinstance(scripts, dict):
        m.scripts = {str(k): str(v) for k, v in scripts.items()}
    return m


def _parse_requirements(root: Path) -> Manifest | None:
    p = root / "requirements.txt"
    if not p.exists():
        return None
    text = _read_text(p)
    if text is None:
        return None
    m = Manifest(name="requirements.txt")
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("-"):
            continue
        # name[extras]==1.2.3 / name>=1.0 / name
        match = re.match(r"^([A-Za-z0-9_.\-]+)(?:\[[\w,\-]+\])?\s*([<>=!~].*)?$", s)
        if not match:
            continue
        name = match.group(1)
        ver = (match.group(2) or "").strip()
        m.deps.append(Dependency(name=name, version=ver, dev=False, source="requirements.txt"))
    return m


def _parse_pyproject(root: Path) -> Manifest | None:
    p = root / "pyproject.toml"
    if not p.exists():
        return None
    text = _read_text(p)
    if not text:
        return None
    m = Manifest(name="pyproject.toml")

    # PEP 621 [project] dependencies = [...]
    for block_re in (
        r"\[project\][\s\S]*?(?=^\[|\Z)",
        r"\[tool\.poetry\.dependencies\][\s\S]*?(?=^\[|\Z)",
        r"\[tool\.poetry\.dev-dependencies\][\s\S]*?(?=^\[|\Z)",
        r"\[project\.optional-dependencies\.[^\]]+\][\s\S]*?(?=^\[|\Z)",
    ):
        for blk in re.findall(block_re, text, re.MULTILINE):
            is_dev = "dev" in blk[:80].lower()

            # PEP 621 list form: dependencies = ["fastapi>=0.100", ...]
            m_list = re.search(r"dependencies\s*=\s*\[([\s\S]*?)\]", blk)
            if m_list:
                for line in m_list.group(1).splitlines():
                    s = line.strip().strip(",").strip().strip('"').strip("'")
                    if not s or s.startswith("#"):
                        continue
                    parts = re.match(r"^([A-Za-z0-9_.\-]+)\s*([<>=!~].*)?$", s)
                    if parts:
                        m.deps.append(Dependency(
                            name=parts.group(1),
                            version=(parts.group(2) or "").strip(),
                            dev=is_dev, source="pyproject.toml",
                        ))

            # Poetry form: name = "^1.2.3" lines
            for line in blk.splitlines():
                pm = re.match(r'^\s*([A-Za-z0-9_.\-]+)\s*=\s*"([^"]+)"', line)
                if pm and pm.group(1).lower() not in ("python", "name", "version", "description"):
                    m.deps.append(Dependency(
                        name=pm.group(1), version=pm.group(2),
                        dev=is_dev, source="pyproject.toml",
                    ))
    return m


def _parse_environment_yml(root: Path) -> Manifest | None:
    p = root / "environment.yml"
    if not p.exists():
        p = root / "environment.yaml"
        if not p.exists():
            return None
    text = _read_text(p)
    if not text:
        return None
    m = Manifest(name=p.name)
    in_deps = False
    in_pip = False
    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if stripped.startswith("dependencies:"):
            in_deps = True
            in_pip = False
            continue
        if not in_deps:
            continue
        if stripped.startswith("- pip:"):
            in_pip = True
            continue
        if stripped.startswith("- "):
            spec = stripped[2:].strip()
            if not spec or spec.endswith(":"):
                continue
            parts = re.match(r"^([A-Za-z0-9_.\-]+)\s*([<>=!~].*)?$", spec)
            if parts:
                m.deps.append(Dependency(
                    name=parts.group(1),
                    version=(parts.group(2) or "").strip(),
                    dev=False, source=f"{p.name}{' (pip)' if in_pip else ''}",
                ))
    return m


def _parse_cargo(root: Path) -> Manifest | None:
    p = root / "Cargo.toml"
    if not p.exists():
        return None
    text = _read_text(p)
    if not text:
        return None
    m = Manifest(name="Cargo.toml")
    for blk_re, dev in (
        (r"\[dependencies\][\s\S]*?(?=^\[|\Z)", False),
        (r"\[dev-dependencies\][\s\S]*?(?=^\[|\Z)", True),
    ):
        for blk in re.findall(blk_re, text, re.MULTILINE):
            for line in blk.splitlines():
                pm = re.match(r'^\s*([A-Za-z0-9_\-]+)\s*=\s*(.+)$', line)
                if not pm:
                    continue
                name = pm.group(1)
                if name in ("dev-dependencies", "dependencies"):
                    continue
                rhs = pm.group(2).strip()
                ver_match = re.search(r'"([^"]+)"', rhs)
                ver = ver_match.group(1) if ver_match else rhs[:60]
                m.deps.append(Dependency(name=name, version=ver, dev=dev, source="Cargo.toml"))
    return m


def _parse_gomod(root: Path) -> Manifest | None:
    p = root / "go.mod"
    if not p.exists():
        return None
    text = _read_text(p)
    if not text:
        return None
    m = Manifest(name="go.mod")
    in_block = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("require ("):
            in_block = True
            continue
        if line == ")":
            in_block = False
            continue
        if line.startswith("require ") and "(" not in line:
            spec = line[len("require "):].strip()
            parts = spec.split()
            if parts:
                m.deps.append(Dependency(
                    name=parts[0], version=parts[1] if len(parts) > 1 else "",
                    dev=False, source="go.mod",
                ))
        elif in_block:
            parts = line.split()
            if len(parts) >= 1 and "/" in parts[0]:
                m.deps.append(Dependency(
                    name=parts[0], version=parts[1] if len(parts) > 1 else "",
                    dev=False, source="go.mod",
                ))
    return m


def _parse_composer(root: Path) -> Manifest | None:
    p = root / "composer.json"
    if not p.exists():
        return None
    text = _read_text(p)
    if not text:
        return None
    try:
        data = json.loads(text)
    except Exception:
        return None
    m = Manifest(name="composer.json")
    for d in (data.get("require") or {}).items():
        m.deps.append(Dependency(name=d[0], version=str(d[1] or ""), dev=False, source="composer.json"))
    for d in (data.get("require-dev") or {}).items():
        m.deps.append(Dependency(name=d[0], version=str(d[1] or ""), dev=True, source="composer.json"))
    return m


def _parse_gemfile(root: Path) -> Manifest | None:
    p = root / "Gemfile"
    if not p.exists():
        return None
    text = _read_text(p)
    if not text:
        return None
    m = Manifest(name="Gemfile")
    for line in text.splitlines():
        gm = re.match(r"""^\s*gem\s+['"]([\w\-]+)['"](?:\s*,\s*['"]([^'"]+)['"])?""", line)
        if gm:
            m.deps.append(Dependency(
                name=gm.group(1), version=(gm.group(2) or ""),
                dev="group :development" in text, source="Gemfile",
            ))
    return m


def _parse_pubspec(root: Path) -> Manifest | None:
    p = root / "pubspec.yaml"
    if not p.exists():
        return None
    text = _read_text(p)
    if not text:
        return None
    m = Manifest(name="pubspec.yaml")
    block: str | None = None
    for raw in text.splitlines():
        if not raw.startswith(" ") and raw.strip().endswith(":"):
            head = raw.strip().rstrip(":")
            if head in ("dependencies", "dev_dependencies"):
                block = head
                continue
            block = None
            continue
        if block and raw.startswith("  ") and ":" in raw:
            key, _, val = raw.strip().partition(":")
            key = key.strip()
            val = val.strip()
            if key and not key.startswith("#"):
                m.deps.append(Dependency(
                    name=key, version=val,
                    dev=block == "dev_dependencies", source="pubspec.yaml",
                ))
    return m


_PARSERS = (
    _parse_package_json,
    _parse_requirements,
    _parse_pyproject,
    _parse_environment_yml,
    _parse_cargo,
    _parse_gomod,
    _parse_composer,
    _parse_gemfile,
    _parse_pubspec,
)


# --- Aggregate read --------------------------------------------------------

def read_dependencies(root: Path | None = None) -> list[Manifest]:
    """Parse every manifest at the workspace root. Returns one Manifest per file found."""
    root = (root or project_profile().root).resolve()
    out: list[Manifest] = []
    for parser in _PARSERS:
        try:
            m = parser(root)
        except Exception:
            m = None
        if m is not None and (m.deps or m.scripts):
            out.append(m)
    return out


def all_dependencies(root: Path | None = None) -> list[Dependency]:
    """Flatten every manifest's deps into one list."""
    flat: list[Dependency] = []
    for m in read_dependencies(root):
        flat.extend(m.deps)
    return flat


def deps_block(root: Path | None = None, max_per_manifest: int = 12) -> str:
    """Compact human-readable summary for system-prompt injection."""
    manifests = read_dependencies(root)
    if not manifests:
        return ""

    lines: list[str] = []
    for m in manifests:
        prod = [d for d in m.deps if not d.dev]
        dev = [d for d in m.deps if d.dev]
        kept_prod = prod[:max_per_manifest]
        kept_dev = dev[: max(0, max_per_manifest - len(kept_prod))]

        head = f"  ### {m.name}  ({len(prod)} deps"
        if dev:
            head += f", {len(dev)} dev"
        head += ")"
        lines.append(head)

        if kept_prod:
            names = ", ".join(d.name for d in kept_prod)
            extra = "" if len(prod) <= len(kept_prod) else f" …(+{len(prod) - len(kept_prod)})"
            lines.append(f"    deps: {names}{extra}")
        if kept_dev:
            names = ", ".join(d.name for d in kept_dev)
            extra = "" if len(dev) <= len(kept_dev) else f" …(+{len(dev) - len(kept_dev)})"
            lines.append(f"    dev:  {names}{extra}")
        if m.scripts:
            keys = list(m.scripts.keys())[:6]
            extra = "" if len(m.scripts) <= len(keys) else f" …(+{len(m.scripts) - len(keys)})"
            lines.append(f"    scripts: {', '.join(keys)}{extra}")

    return "\n\n## Dependencies (auto-detected)\n" + "\n".join(lines) + "\n"


# --- Install dispatch ------------------------------------------------------

def install_command(profile: ProjectProfile, name: str, dev: bool = False) -> str | None:
    """Return the shell command to install `name` for the detected stack.

    Returns None if no package manager has been detected for the workspace.
    The caller is expected to feed this into `shell_exec`.
    """
    pm = (profile.package_manager or "").lower()
    name = name.strip()
    if not name:
        return None

    if pm == "npm":
        return f"npm install {'--save-dev ' if dev else ''}{name}"
    if pm == "pnpm":
        return f"pnpm add {'-D ' if dev else ''}{name}"
    if pm == "yarn":
        return f"yarn add {'-D ' if dev else ''}{name}"
    if pm == "bun":
        return f"bun add {'-d ' if dev else ''}{name}"
    if pm == "uv":
        return f"uv add {'--dev ' if dev else ''}{name}"
    if pm == "poetry":
        return f"poetry add {'--group dev ' if dev else ''}{name}"
    if pm == "pip":
        return f"pip install {name}"
    if pm == "cargo":
        return f"cargo add {'--dev ' if dev else ''}{name}"
    if pm == "go":
        return f"go get {name}"
    return None


def uninstall_command(profile: ProjectProfile, name: str) -> str | None:
    pm = (profile.package_manager or "").lower()
    name = name.strip()
    if not name:
        return None
    if pm == "npm":
        return f"npm uninstall {name}"
    if pm == "pnpm":
        return f"pnpm remove {name}"
    if pm == "yarn":
        return f"yarn remove {name}"
    if pm == "bun":
        return f"bun remove {name}"
    if pm == "uv":
        return f"uv remove {name}"
    if pm == "poetry":
        return f"poetry remove {name}"
    if pm == "pip":
        return f"pip uninstall -y {name}"
    if pm == "cargo":
        return f"cargo remove {name}"
    return None


def sync_command(profile: ProjectProfile) -> str | None:
    """The "install everything from the manifest" command."""
    pm = (profile.package_manager or "").lower()
    if pm == "npm":
        return "npm install"
    if pm == "pnpm":
        return "pnpm install"
    if pm == "yarn":
        return "yarn install"
    if pm == "bun":
        return "bun install"
    if pm == "uv":
        return "uv sync"
    if pm == "poetry":
        return "poetry install"
    if pm == "pip":
        return "pip install -r requirements.txt"
    if pm == "cargo":
        return "cargo build"
    if pm == "go":
        return "go mod download"
    return None
