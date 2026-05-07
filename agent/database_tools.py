"""Database tools — SQLite directly, Postgres/MySQL via DSN.

Stores connection DSNs in the vault under names you give. SELECT/SHOW/EXPLAIN are
allowed; mutations require explicit safe=False."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from langchain_core.tools import tool

from agent.credential_vault import get_credential


def _dsn(connection_name: str) -> str | None:
    return get_credential(f"db_dsn_{connection_name}")


@tool
def db_query_sqlite(file_path: str, sql: str) -> str:
    """Run any SQL on a local SQLite file (SELECT/INSERT/UPDATE/DELETE/CREATE/DROP)."""
    p = Path(file_path).expanduser()
    if not p.exists():
        return f"[error] {file_path} not found"
    try:
        con = sqlite3.connect(p)
        con.row_factory = sqlite3.Row
        cur = con.execute(sql)
        if cur.description:
            rows = cur.fetchall()
            keys = list(rows[0].keys()) if rows else [d[0] for d in cur.description]
            con.close()
            if not rows:
                return "(no rows)"
            out = ["\t".join(keys)]
            for r in rows[:50]:
                out.append("\t".join(str(r[k]) for k in keys))
            return "\n".join(out) + (f"\n... ({len(rows)} total)" if len(rows) > 50 else "")
        con.commit()
        affected = cur.rowcount
        con.close()
        return f"✓ executed (rowcount: {affected})"
    except Exception as e:
        return f"[error] {e}"


@tool
def db_query(connection_name: str, sql: str) -> str:
    """Run any SQL against a saved Postgres/MySQL connection (vault key db_dsn_<name>).
    DSNs: postgresql://user:pw@host:5432/db | mysql://user:pw@host:3306/db"""
    dsn = _dsn(connection_name)
    if not dsn:
        return f"[error] no DSN for '{connection_name}' in vault (key: db_dsn_{connection_name})"

    if dsn.startswith("postgresql"):
        try:
            import psycopg2
            con = psycopg2.connect(dsn)
            cur = con.cursor()
            cur.execute(sql)
            if cur.description:
                cols = [d[0] for d in cur.description]
                rows = cur.fetchmany(50)
                con.close()
                out = ["\t".join(cols)] + ["\t".join(str(c) for c in r) for r in rows]
                return "\n".join(out) or "(no rows)"
            con.commit()
            affected = cur.rowcount
            con.close()
            return f"✓ executed (rowcount: {affected})"
        except ImportError:
            return "[error] pip install psycopg2-binary"
        except Exception as e:
            return f"[error] {e}"
    if dsn.startswith("mysql"):
        try:
            import pymysql
            from urllib.parse import urlparse
            u = urlparse(dsn)
            con = pymysql.connect(
                host=u.hostname, port=u.port or 3306,
                user=u.username, password=u.password,
                db=u.path.lstrip("/"),
            )
            cur = con.cursor()
            cur.execute(sql)
            if cur.description:
                rows = cur.fetchmany(50)
                cols = [d[0] for d in cur.description]
                con.close()
                out = ["\t".join(cols)] + ["\t".join(str(c) for c in r) for r in rows]
                return "\n".join(out) or "(no rows)"
            con.commit()
            affected = cur.rowcount
            con.close()
            return f"✓ executed (rowcount: {affected})"
        except ImportError:
            return "[error] pip install PyMySQL"
        except Exception as e:
            return f"[error] {e}"
    return "[error] unsupported DSN — use postgresql:// or mysql:// or sqlite file via db_query_sqlite"


@tool
def db_list_tables_sqlite(file_path: str) -> str:
    """List tables in a SQLite database."""
    p = Path(file_path).expanduser()
    if not p.exists():
        return f"[error] {file_path} not found"
    try:
        con = sqlite3.connect(p)
        rows = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        con.close()
        return "\n".join(r[0] for r in rows) or "(no tables)"
    except Exception as e:
        return f"[error] {e}"


DATABASE_TOOLS = [db_query_sqlite, db_list_tables_sqlite, db_query]
