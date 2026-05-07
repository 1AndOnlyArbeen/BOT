#!/usr/bin/env python3
"""Ingest curated SEED patterns into the code library so Ultron has a knowledge base."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.seed_patterns import SEED
from agent.seed_patterns_nodejs import NODEJS_SEED
from agent.seed_patterns_web import WEB_SEED
from agent.seed_patterns_backend_deep import BACKEND_DEEP_SEED
from agent.code_library import save_pattern


ALL_PATTERNS = SEED + NODEJS_SEED + WEB_SEED + BACKEND_DEEP_SEED


def run() -> dict:
    saved = 0
    for entry in ALL_PATTERNS:
        save_pattern(
            request=entry["request"],
            code=entry["code"],
            language=entry.get("language", "text"),
            notes=entry.get("framework", ""),
            success=True,
        )
        saved += 1
    return {"saved": saved, "topics": _topic_breakdown()}


def _topic_breakdown() -> dict:
    out: dict = {}
    for e in ALL_PATTERNS:
        fw = e.get("framework", "other")
        out[fw] = out.get(fw, 0) + 1
    return out


if __name__ == "__main__":
    result = run()
    print(f"✓ seeded {result['saved']} patterns")
    for fw, n in sorted(result["topics"].items(), key=lambda x: -x[1]):
        print(f"  {fw}: {n}")
