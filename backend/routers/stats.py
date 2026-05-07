"""Stats dashboard data."""
from __future__ import annotations

from fastapi import APIRouter

from agent import audit
from agent import episodic, knowledge_graph as kg
from agent.learning import all_memories
from agent.memory import list_sessions

router = APIRouter()


@router.get("/")
def overview() -> dict:
    sessions = list_sessions()
    return {
        "sessions": len(sessions),
        "memories": len(all_memories()),
        "episodes": episodic.stats().get("count", 0),
        "entities": len(kg.list_entities(limit=10000)),
        "audit_24h": audit.stats(24),
    }


@router.get("/audit")
def audit_log(limit: int = 100, tool: str | None = None) -> list[dict]:
    return audit.recent(limit=limit, tool=tool)


@router.get("/audit/by-tool")
def audit_by_tool(window_hours: int = 24) -> dict:
    return audit.stats(window_hours=window_hours)
