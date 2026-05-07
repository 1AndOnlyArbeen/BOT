"""Credential vault (metadata only — values never returned over API)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent.credential_vault import (
    set_credential, get_credential, delete_credential, list_credentials,
)


router = APIRouter()


class SetCredBody(BaseModel):
    name: str
    value: str
    kind: str = "secret"


@router.get("/")
def list_all() -> list[dict]:
    return list_credentials()


@router.post("/")
def add(body: SetCredBody) -> dict:
    ok = set_credential(body.name, body.value, body.kind)
    if not ok:
        raise HTTPException(500, "keyring unavailable — install python-keyring + libsecret backend")
    return {"ok": True}


@router.delete("/{name}")
def remove(name: str) -> dict:
    return {"ok": delete_credential(name)}
