"""Saved macros API."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent import macros as M

router = APIRouter()


class SaveMacro(BaseModel):
    name: str
    prompt: str
    description: str = ""


@router.get("/")
def list_all() -> list[dict]:
    return M.list_macros()


@router.post("/")
def save(body: SaveMacro) -> dict:
    return M.save_macro(body.name, body.prompt, body.description)


@router.delete("/{name}")
def delete(name: str) -> dict:
    if not M.delete_macro(name):
        raise HTTPException(404)
    return {"ok": True}


@router.post("/{name}/run")
def run(name: str) -> dict:
    m = M.get_macro(name)
    if not m:
        raise HTTPException(404)
    M.increment_run(name)
    return m
