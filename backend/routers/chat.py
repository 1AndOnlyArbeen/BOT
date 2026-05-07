"""Chat endpoints: sessions, messages, streaming."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent.graph import stream_agent, _persist_turn
from agent.planner import make_plan, execute_plan
from agent.memory import (
    add_message, delete_session, get_messages,
    list_sessions, new_session, rename_session,
)


router = APIRouter()


class ChatRequest(BaseModel):
    session_id: int
    message: str
    mode: str = "ultron"
    use_planner: bool = True


class NewSessionBody(BaseModel):
    title: str = "New chat"
    mode: str = "ultron"


class RenameBody(BaseModel):
    title: str


@router.get("/sessions")
def sessions(mode: str | None = None) -> list[dict]:
    return list_sessions(mode=mode)


@router.post("/sessions")
def create_session(body: NewSessionBody) -> dict:
    sid = new_session(body.title, mode=body.mode)
    return {"id": sid, "title": body.title, "mode": body.mode}


@router.delete("/sessions/{session_id}")
def remove_session(session_id: int) -> dict:
    delete_session(session_id)
    return {"ok": True}


@router.patch("/sessions/{session_id}")
def patch_session(session_id: int, body: RenameBody) -> dict:
    rename_session(session_id, body.title)
    return {"ok": True}


@router.get("/sessions/{session_id}/messages")
def messages(session_id: int) -> list[dict]:
    return get_messages(session_id)


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


def _auto_title(text: str) -> str:
    t = text.strip().split("\n")[0]
    return (t[:40] + "…") if len(t) > 40 else t


@router.post("/stream")
def stream(req: ChatRequest):
    """SSE stream of router/tool/token events for one chat turn."""
    if not get_messages(req.session_id):
        rename_session(req.session_id, _auto_title(req.message))

    add_message(req.session_id, "user", req.message)

    def gen():
        history = get_messages(req.session_id)[:-1]

        if req.mode == "ultron" and req.use_planner:
            plan = make_plan(req.message)
            yield _sse({"type": "plan", "data": {
                "request": plan.request,
                "steps": [{"index": s.index, "goal": s.goal, "rationale": s.rationale} for s in plan.steps],
            }})

            collected: list[str] = []
            for ev in execute_plan(plan, history=history):
                yield _sse(ev)
                if ev["type"] == "step_end":
                    collected.append(f"[{ev['data']['index']}] {ev['data']['result']}")
                if ev["type"] == "plan_done":
                    final = ev["data"]["summary"] or "\n".join(collected)
                    add_message(req.session_id, "assistant", final)
                    _persist_turn(req.message, final, req.session_id)
                    yield _sse({"type": "final", "data": final})
            return

        final = ""
        for ev in stream_agent(req.message, history=history, mode=req.mode):
            if ev["type"] == "token":
                final = ev["data"]
            if ev["type"] == "final":
                final = ev["data"] or final
            yield _sse(ev)

        if final and not final.startswith("⚠"):
            add_message(req.session_id, "assistant", final)
            _persist_turn(req.message, final, req.session_id)

    return StreamingResponse(gen(), media_type="text/event-stream")
