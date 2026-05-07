"""Lightweight knowledge graph — entities (people, projects, files) and their relationships.

Stored as SQLite triples: (subject, predicate, object). Queryable by entity."""
from __future__ import annotations

import re
import sqlite3
import time
from contextlib import contextmanager

from langchain_ollama import ChatOllama

from config import DATA_DIR, LLM_MODEL


KG_DB = DATA_DIR / "knowledge_graph.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS entities (
    name TEXT PRIMARY KEY,
    kind TEXT,
    first_seen REAL,
    last_seen REAL,
    mentions INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS triples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object TEXT NOT NULL,
    ts REAL NOT NULL,
    UNIQUE(subject, predicate, object)
);
CREATE INDEX IF NOT EXISTS idx_subj ON triples(subject);
CREATE INDEX IF NOT EXISTS idx_obj ON triples(object);
"""


@contextmanager
def _conn():
    c = sqlite3.connect(KG_DB)
    try:
        yield c
        c.commit()
    finally:
        c.close()


def _init():
    with _conn() as c:
        c.executescript(SCHEMA)


_init()


EXTRACT_PROMPT = """Extract knowledge triples from the text. Each triple is (subject, predicate, object).
Subjects/objects should be specific entities (people, projects, files, technologies). Skip generic facts.

Output JSON only:
{{"triples": [["Subject", "predicate", "Object"], ...]}}

If nothing extractable: {{"triples": []}}

Text: {text}

JSON:"""


def _llm():
    return ChatOllama(model=LLM_MODEL, temperature=0.0, num_predict=300, format="json")


def extract_triples(text: str) -> list[tuple[str, str, str]]:
    if len(text) < 40:
        return []
    try:
        import json
        resp = _llm().invoke(EXTRACT_PROMPT.format(text=text[:1500])).content
        clean = re.sub(r"<think>.*?</think>", "", resp, flags=re.DOTALL).strip()
        data = json.loads(clean)
        out = []
        for t in data.get("triples", [])[:10]:
            if isinstance(t, list) and len(t) == 3 and all(isinstance(x, str) and x.strip() for x in t):
                out.append((t[0].strip()[:80], t[1].strip()[:60], t[2].strip()[:120]))
        return out
    except Exception:
        return []


def add_triple(subject: str, predicate: str, obj: str) -> None:
    now = time.time()
    with _conn() as c:
        for name in (subject, obj):
            c.execute(
                "INSERT INTO entities(name, first_seen, last_seen, mentions) VALUES (?,?,?,1) "
                "ON CONFLICT(name) DO UPDATE SET last_seen=excluded.last_seen, mentions=mentions+1",
                (name, now, now),
            )
        try:
            c.execute(
                "INSERT INTO triples(subject, predicate, object, ts) VALUES (?,?,?,?)",
                (subject, predicate, obj, now),
            )
        except sqlite3.IntegrityError:
            pass


def learn_from_text(text: str) -> int:
    triples = extract_triples(text)
    for s, p, o in triples:
        add_triple(s, p, o)
    return len(triples)


def query_entity(name: str) -> dict:
    with _conn() as c:
        ent = c.execute(
            "SELECT name, kind, mentions FROM entities WHERE name LIKE ?",
            (f"%{name}%",),
        ).fetchall()
        outgoing = c.execute(
            "SELECT predicate, object FROM triples WHERE subject LIKE ?",
            (f"%{name}%",),
        ).fetchall()
        incoming = c.execute(
            "SELECT subject, predicate FROM triples WHERE object LIKE ?",
            (f"%{name}%",),
        ).fetchall()
    return {
        "matches": [{"name": e[0], "kind": e[1], "mentions": e[2]} for e in ent],
        "outgoing": [{"predicate": p, "object": o} for p, o in outgoing],
        "incoming": [{"subject": s, "predicate": p} for s, p in incoming],
    }


def list_entities(limit: int = 50) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT name, kind, mentions, last_seen FROM entities ORDER BY mentions DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"name": r[0], "kind": r[1], "mentions": r[2], "last_seen": r[3]} for r in rows]


def all_triples(limit: int = 200) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT subject, predicate, object, ts FROM triples ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"s": r[0], "p": r[1], "o": r[2], "ts": r[3]} for r in rows]


def kg_context(query: str, max_lines: int = 8) -> str:
    """Format relevant KG facts for prompt injection."""
    keywords = re.findall(r"\b[A-Z][\w]{2,}\b", query)
    if not keywords:
        return ""
    seen = set()
    facts = []
    for kw in keywords[:5]:
        info = query_entity(kw)
        for o in info["outgoing"][:3]:
            line = f"{kw} {o['predicate']} {o['object']}"
            if line not in seen:
                seen.add(line)
                facts.append(line)
        for i in info["incoming"][:2]:
            line = f"{i['subject']} {i['predicate']} {kw}"
            if line not in seen:
                seen.add(line)
                facts.append(line)
        if len(facts) >= max_lines:
            break
    if not facts:
        return ""
    return "\n\nKNOWN ENTITIES:\n" + "\n".join(f"- {f}" for f in facts[:max_lines]) + "\n"


def reset() -> None:
    with _conn() as c:
        c.execute("DELETE FROM triples")
        c.execute("DELETE FROM entities")
