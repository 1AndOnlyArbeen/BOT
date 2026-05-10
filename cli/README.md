# `cli/` — Ultron's Claude-Code-style coder

This package powers the **Coder** mode. It replaces the legacy `agent.graph`
flow for `mode == "coder"` with a focused, project-aware coding loop that
mirrors how Claude Code is structured.

The legacy `agent/` package is **not** removed — Chat mode and Ultron's old
shortcuts still go through it, and `cli/` reuses several of its primitives
(`agent.file_tools`, `agent.file_search`, `agent.shell_tools`,
`agent.codebase_tools`, `agent.verify`). The point of `cli/` is composition,
not reinvention.

## Folder layout

```
cli/
├── README.md            ← you are here
├── __init__.py          ← public surface (re-exports cli.runner.run)
├── runner.py            ← entry: cli.runner.run(message, history) -> events
├── agent.py             ← explore → plan → act → verify loop
├── prompts.py           ← modular system-prompt builder
├── session.py           ← per-turn scratchpad (last_written, plan, …)
├── project/
│   ├── detect.py        ← sniff package.json / pyproject.toml / Cargo.toml…
│   ├── notes.py         ← read/maintain ULTRON.md project-memory file
│   └── primer.py        ← folder tree + profile + notes → prompt block
└── tools/
    ├── __init__.py      ← curated tool list for coder mode
    └── project.py       ← project_info, update_notes (new tools)
```

## Why these splits?

| Concern | Module | Notes |
| --- | --- | --- |
| What kind of project is this? | `project/detect.py` | Pure inspection — no LLM. Cached per workspace. |
| How does Ultron remember conventions? | `project/notes.py` | `ULTRON.md` at workspace root, hand-editable. |
| What does the model see at the top of every turn? | `project/primer.py` | Profile + notes + folder tree, capped. |
| How does the model think about a turn? | `agent.py` | Intent → optional plan → tool loop → verify. |
| What can the model actually do? | `tools/__init__.py` | Curated, workspace-scoped, sandboxed. |
| What's the prompt? | `prompts.py` | Modular blocks: role / workflow / quality bar / context. |
| What survives across turns? | `project/notes.py` (durable) + `session.py` (per-turn) | |

## The loop

```
cli.runner.run(message, history)
        │
        ▼
agent.handle_turn(message, history)
        │
        ├── 1. classify_intent(message)        → question | read | edit | run | init
        │
        ├── 2. project_profile(workspace)      → cached ProjectProfile
        ├── 3. read_or_init_notes(profile)     → ULTRON.md text (auto-created)
        ├── 4. build_primer(profile, notes)    → system-prompt block
        │
        ├── 5. (optional) plan if intent is complex → emit cli_plan event
        │
        ├── 6. create_react_agent(LLM, tools, system_prompt)
        │       loop until done, yielding tool_call / tool_result / token
        │
        └── 7. if a file was written → verify (syntax/lint)
                if errors → one retry with errors injected
                if clean → emit verify_ok
```

Each step yields events the chat router forwards to the UI.

## Reused agent/ primitives

These are imported (not duplicated) because they already work:

- `agent.file_tools` — `read_file`, `write_file`, `edit_file`, `make_folder`,
  `delete_file`, `undo_last_edit`, `list_files`, `run_python_file`.
  Already workspace-scoped; we expose them as-is.
- `agent.file_search` — `find_files`, `grep_files`, `file_info`, `list_dir`.
- `agent.shell_tools` — `shell_exec` only (the others are too risky for the
  coder default toolset).
- `agent.codebase_tools` — `codebase_search`, `codebase_explain_how_to`,
  `codebase_show_file`. Used when an indexed repo exists.
- `agent.verify.verify_file` — language-aware syntax check after write.
- `agent.confirmations` — confirmation gating when context demands it.

## Why ULTRON.md?

Anything the user wants Ultron to remember **about this specific project**
goes here. Conventions ("we use 4-space indent"), commands ("test:
`uv run pytest`"), focus area ("currently rewriting the auth flow"). It's a
plain markdown file — git-friendly, hand-editable, and survives across chat
sessions because it lives next to the code, not in a database.

## Adding a new tool

1. Define it in `cli/tools/<topic>.py` using the `@tool` decorator from
   `langchain_core.tools` (matches everything else).
2. Register it in `cli/tools/__init__.py` → `CODER_TOOLS`.
3. Mention it briefly in `cli/prompts.py` if the model needs a hint.

That's it — no other files to touch.
