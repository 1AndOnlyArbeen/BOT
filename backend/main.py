"""FastAPI backend for Ultron. Mounts all sub-routers and serves the React frontend."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.routers import (
    chat, files, memory, voice, macros,
    calendar, stats, system, vault, codebase, training,
)


app = FastAPI(title="Ultron API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    from config import LLM_MODEL
    return {"ok": True, "model": LLM_MODEL, "version": "3.0.0"}


app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(memory.router, prefix="/api/memory", tags=["memory"])
app.include_router(voice.router, prefix="/api/voice", tags=["voice"])
app.include_router(macros.router, prefix="/api/macros", tags=["macros"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["calendar"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])
app.include_router(system.router, prefix="/api/system", tags=["system"])
app.include_router(vault.router, prefix="/api/vault", tags=["vault"])
app.include_router(codebase.router, prefix="/api/codebase", tags=["codebase"])
app.include_router(training.router, prefix="/api/training", tags=["training"])


_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="frontend")
