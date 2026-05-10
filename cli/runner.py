"""Public entry point for the coder CLI.

The chat router (in agent/graph.py) calls `cli.runner.run()` whenever the
user is in coder mode. This module is intentionally tiny — almost all
logic lives in cli.agent.
"""
from __future__ import annotations

from typing import Iterator

from cli.agent import handle_turn


def run(message: str, history: list[dict] | None = None) -> Iterator[dict]:
    """Run one coder turn. Yields stream events for SSE."""
    yield from handle_turn(message, history=history)
