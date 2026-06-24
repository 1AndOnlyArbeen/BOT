"""Incremental folder ingestion for the RAG brain.

Feeds an entire project folder (code + docs) into the same Chroma store the
brain reads from, and is safe to re-run: only NEW or CHANGED files are
re-embedded, and files deleted on disk are removed from the store. Each chunk
is labelled with its path relative to the folder's parent (e.g.
``baldar/app/Http/Controllers/Foo.php``) so retrieval citations point at the
real file, and so per-file updates can replace cleanly.

Usage:
    python -m rag.ingest_folder                      # default: ../baldar
    python -m rag.ingest_folder /abs/path/to/project
    python -m rag.ingest_folder ../baldar --reset    # wipe this folder first
"""
from __future__ import annotations

import sys
from pathlib import Path

from langchain_core.documents import Document

from config import BASE_DIR
from rag.ingest import get_vectorstore, _split, _load_one

# Default target: the `baldar` project sitting next to the BOT repo.
#   BASE_DIR = .../Development/BOT/BOT  ->  .../Development/baldar
DEFAULT_TARGET = (BASE_DIR / ".." / ".." / "baldar").resolve()

# Only these extensions are ingested (code + docs + config).
INCLUDE_EXT = {
    ".php", ".py", ".js", ".jsx", ".ts", ".tsx", ".vue", ".go", ".rb",
    ".java", ".cs", ".cpp", ".c", ".h", ".rs", ".swift", ".kt",
    ".html", ".css", ".scss", ".sass",
    ".json", ".yaml", ".yml", ".toml", ".xml", ".ini", ".env.example",
    ".md", ".mdx", ".txt", ".rst",
    ".sql", ".sh", ".bash", ".blade.php",
}

# Directories never worth feeding (deps, build output, VCS, caches).
SKIP_DIRS = {
    "node_modules", "vendor", ".git", ".svn", ".hg",
    "dist", "build", ".next", ".nuxt", ".output", "out",
    ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".cache", "coverage", ".idea", ".vscode",
    "bootstrap/cache",  # Laravel compiled cache
}

# Individual files to skip (lock files, minified bundles — huge, low value).
SKIP_FILE_SUFFIXES = (".min.js", ".min.css", ".map")
SKIP_FILE_NAMES = {
    "composer.lock", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
}

MAX_BYTES = 1_500_000  # skip anything larger than ~1.5 MB


def _match_ext(name: str) -> bool:
    lname = name.lower()
    # handle double extensions like .blade.php / .env.example
    return any(lname.endswith(ext) for ext in INCLUDE_EXT)


def _should_skip_dir(path: Path, root: Path) -> bool:
    rel_parts = path.relative_to(root).parts
    return any(part in SKIP_DIRS for part in rel_parts)


def _collect_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if _should_skip_dir(p.parent, root):
            continue
        if p.name in SKIP_FILE_NAMES:
            continue
        if any(p.name.lower().endswith(s) for s in SKIP_FILE_SUFFIXES):
            continue
        if not _match_ext(p.name):
            continue
        try:
            if p.stat().st_size > MAX_BYTES:
                continue
        except OSError:
            continue
        files.append(p)
    return files


def _existing_index(vs, prefix: str) -> dict[str, int]:
    """Map source-label -> stored mtime, for chunks under this folder prefix."""
    index: dict[str, int] = {}
    try:
        data = vs.get(include=["metadatas"])
    except Exception:
        return index
    for meta in data.get("metadatas", []) or []:
        src = (meta or {}).get("source", "")
        if src.startswith(prefix):
            index[src] = int((meta or {}).get("mtime", 0))
    return index


def ingest_folder(target: Path, reset: bool = False) -> None:
    target = target.resolve()
    if not target.is_dir():
        print(f"error: not a directory: {target}")
        sys.exit(1)

    label_root = target.parent  # so labels read "baldar/..."
    prefix = target.name + "/"
    vs = get_vectorstore()

    if reset:
        # remove every chunk currently under this folder prefix
        try:
            data = vs.get(include=["metadatas"])
            ids = [
                _id for _id, m in zip(data.get("ids", []), data.get("metadatas", []))
                if (m or {}).get("source", "").startswith(prefix)
            ]
            if ids:
                vs.delete(ids=ids)
                print(f"[reset] removed {len(ids)} existing chunks under {prefix}")
        except Exception as e:
            print(f"[reset] skipped ({e})")

    files = _collect_files(target)
    existing = {} if reset else _existing_index(vs, prefix)
    current_labels: set[str] = set()

    new_files, changed_files, unchanged = [], [], 0
    for f in files:
        label = str(f.relative_to(label_root))
        current_labels.add(label)
        mtime = int(f.stat().st_mtime)
        if label not in existing:
            new_files.append((f, label, mtime))
        elif existing[label] != mtime:
            changed_files.append((f, label, mtime))
        else:
            unchanged += 1

    # files removed from disk -> drop from store
    removed = [lbl for lbl in existing if lbl not in current_labels]

    print(f"target      : {target}")
    print(f"on disk     : {len(files)} ingestable files")
    print(f"new         : {len(new_files)}")
    print(f"changed     : {len(changed_files)}")
    print(f"unchanged   : {unchanged}")
    print(f"removed     : {len(removed)}")

    # delete old chunks for changed + removed sources
    to_delete = [lbl for (_f, lbl, _m) in changed_files] + removed
    for lbl in to_delete:
        try:
            vs.delete(where={"source": lbl})
        except Exception as e:
            print(f"  ! delete failed for {lbl}: {e}")

    # embed new + changed
    to_embed = new_files + changed_files
    total_chunks = 0
    for i, (f, label, mtime) in enumerate(to_embed, 1):
        loaded = _load_one(f)
        for d in loaded:
            d.metadata["source"] = label
            d.metadata["mtime"] = mtime
        if not loaded:
            continue
        chunks = _split(loaded)
        if not chunks:
            continue
        try:
            vs.add_documents(chunks)
            total_chunks += len(chunks)
        except Exception as e:
            print(f"  ! embed failed for {label}: {e}")
        if i % 25 == 0 or i == len(to_embed):
            print(f"  embedded {i}/{len(to_embed)} files ({total_chunks} chunks)")

    print(f"done. {total_chunks} chunks added/updated.")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    reset = "--reset" in sys.argv[1:]
    target = Path(args[0]).expanduser() if args else DEFAULT_TARGET
    ingest_folder(target, reset=reset)


if __name__ == "__main__":
    main()
