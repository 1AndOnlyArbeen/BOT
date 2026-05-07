"""Memory endpoints: facts, episodic, knowledge graph."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from agent.learning import all_memories, forget_all, forget_one, remember
from agent import episodic, knowledge_graph as kg

router = APIRouter()


class AddFact(BaseModel):
    text: str


class SearchBody(BaseModel):
    query: str
    k: int = 5


@router.get("/facts")
def facts() -> list[dict]:
    return all_memories()


@router.post("/facts")
def add_fact(body: AddFact) -> dict:
    n = remember([body.text])
    return {"saved": n}


@router.delete("/facts")
def delete_fact(text: str) -> dict:
    return {"ok": forget_one(text)}


@router.delete("/facts/all")
def wipe_facts() -> dict:
    forget_all()
    return {"ok": True}


@router.post("/episodic/search")
def episodic_search(body: SearchBody) -> list[dict]:
    return episodic.recall_episodes(body.query, k=body.k)


@router.get("/episodic/stats")
def episodic_stats() -> dict:
    return episodic.stats()


@router.delete("/episodic")
def reset_episodic() -> dict:
    episodic.reset()
    return {"ok": True}


@router.get("/kg/entities")
def entities(limit: int = 50) -> list[dict]:
    return kg.list_entities(limit=limit)


@router.get("/kg/triples")
def triples(limit: int = 200) -> list[dict]:
    return kg.all_triples(limit=limit)


@router.get("/kg/query")
def query_entity(name: str) -> dict:
    return kg.query_entity(name)


@router.delete("/kg")
def reset_kg() -> dict:
    kg.reset()
    return {"ok": True}
