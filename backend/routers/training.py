"""Library training: seed curated stack patterns + learn arbitrary topics on demand."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from agent.code_library import list_all
from agent.learn_topic import learn_topic as learn_topic_tool
from scripts.seed_library import run as seed_run


router = APIRouter()


class LearnBody(BaseModel):
    topic: str
    doc_url: str = ""


@router.post("/seed")
def seed() -> dict:
    """Ingest curated patterns for Express, React, Mongo, Postgres, Django, Docker, k8s, etc."""
    return seed_run()


@router.get("/library")
def library() -> list[dict]:
    return list_all()


@router.post("/learn")
def learn(body: LearnBody) -> dict:
    msg = learn_topic_tool.invoke({"topic": body.topic, "doc_url": body.doc_url})
    return {"message": msg}
