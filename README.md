# 🦾 ULTRON v3

**Local Jarvis-style AI assistant.** Voice, vision, system control, messaging, code, RAG, web — running entirely on your laptop. **Now with React UI, FastAPI backend, plan-then-execute, episodic memory, knowledge graph, click-by-text, code library, and 100+ tools.**

---

## ✨ What's New In v3

| Layer | Capability |
|-------|-----------|
| **🎨 React + Tailwind UI** | Clean dark theme, beautiful chat, plan/tool live feed, dedicated views for memory, macros, tasks, files, stats, vault |
| **⚡ FastAPI backend** | REST + Server-Sent Events; all features exposed cleanly |
| **🪜 Plan-then-execute** | Multi-step requests → numbered plan → step-by-step execution → recovers on failure |
| **🧠 4-layer memory** | Working (chat) · Semantic (facts) · Episodic (past chats) · Knowledge graph (entities) |
| **🎯 Click-by-text** | "click Submit" — uses OCR to find and click any text on screen |
| **👁 Active-window awareness** | Knows what app you're in and reads only that window |
| **📚 Code library** | Saves working code patterns; reuses on similar future asks (Claude-style) |
| **🌐 Doc-driven coding** | Searches official docs before writing unfamiliar code |
| **🔁 Duplicate-aware learning** | Reinforces existing memories instead of duplicating |
| **🎬 Saved macros** | Named workflows like `morning_brief` you can run with one click |
| **📅 Tasks/calendar** | Full task manager with due dates, priorities, projects |
| **🔐 Credential vault** | OS-keyring-backed; values never returned over API |
| **📊 Stats dashboard** | Tool usage, success rates, recent audit trail |
| **🛡 Permission tiers** | Every tool tagged read/write/system/network/risky |

---

## 🛠 Tool Inventory (~100 tools)

System · Mouse · Vision (OCR + LLaVA) · GUI Smart (click-by-text, active window) · Comms (WhatsApp/Email/Telegram/Social) · Web (search + fetch) · Files (workspace + system) · Processes/Network · Scheduler/Reminders · Calendar/Tasks · Media (yt-dlp/audio) · Git · Documents (PDF/HTML/TTS) · Dev (pip/apt/black) · Browser Automation (Playwright) · Code Library · Knowledge

---

## ▶ Setup

```bash
cd "Arbeen/Development /bot"
./setup.sh
```

Installs system deps, Python venv, Ollama models, AND frontend `npm install`.

## ▶ Run

```bash
./run.sh
```

Opens **backend on :8000** and **frontend dev server on http://localhost:5173**.

For production: build frontend (`cd frontend && npm run build`), then just run uvicorn — backend serves the static UI from `frontend/dist`.

---

## 📂 Project Structure

```
bot/
├── app.py                          legacy Streamlit (still works)
├── run.sh                          start backend + frontend
├── setup.sh                        installer
├── config.py
│
├── backend/                        FastAPI v3
│   ├── main.py
│   └── routers/
│       ├── chat.py                 sessions + SSE stream
│       ├── files.py                workspace + uploads
│       ├── memory.py               facts / episodic / KG
│       ├── voice.py                STT / TTS
│       ├── macros.py
│       ├── calendar.py
│       ├── stats.py
│       ├── system.py
│       └── vault.py
│
├── agent/                          all the brains
│   ├── graph.py                    multi-mode + memory + streaming
│   ├── router.py                   intent → tool subset
│   ├── planner.py                  plan-then-execute
│   ├── tools.py                    catalogues
│   ├── permissions.py              tier per tool
│   ├── audit.py                    append-only call log
│   │
│   ├── learning.py                 semantic facts + duplicate-aware
│   ├── episodic.py                 past-chat embeddings
│   ├── knowledge_graph.py          entities + triples
│   ├── memory.py                   SQLite chat history
│   ├── macros.py                   named workflows
│   ├── code_library.py             save/recall code patterns
│   ├── credential_vault.py         keyring wrapper
│   ├── backup.py                   file undo
│   │
│   ├── system_tools.py             desktop control
│   ├── mouse_tools.py              mouse + brightness
│   ├── gui_smart.py                click-by-text + window-aware
│   ├── vision_tools.py             OCR
│   ├── vision_llm.py               LLaVA / Moondream
│   ├── comm_tools.py               messaging compose
│   ├── web_tools.py                fetch/scrape
│   ├── file_tools.py               workspace ops + undo
│   ├── file_search.py              system-wide search
│   ├── process_tools.py            ps/kill/network
│   ├── scheduler.py                reminders
│   ├── calendar_tools.py           taskwarrior + tasks DB
│   ├── media_tools.py              yt-dlp + recording
│   ├── git_tools.py
│   ├── document_tools.py
│   ├── dev_tools.py
│   └── browser_automation.py       Playwright
│
├── frontend/                       React + Vite + TS + Tailwind
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── api.ts                  typed client
│   │   ├── store.ts                zustand
│   │   ├── types.ts
│   │   └── components/
│   │       ├── Sidebar.tsx
│   │       ├── ChatView.tsx
│   │       ├── MemoryView.tsx
│   │       ├── MacrosView.tsx
│   │       ├── TasksView.tsx
│   │       ├── CoderView.tsx
│   │       ├── StatsView.tsx
│   │       ├── VaultView.tsx
│   │       └── VoiceRecorder.tsx
│
├── voice/                          STT (whisper) + TTS (piper/pyttsx3) + wake-word
├── rag/                            document RAG
├── workspace/                      coder mode operates here
├── deployment/
│   ├── ultron.service              systemd unit
│   └── install_service.sh
└── data/                           all state
    ├── chat.db
    ├── memory/                     facts
    ├── episodic/                   past chats
    ├── knowledge_graph.db          entity/triples
    ├── chroma/                     RAG docs
    ├── code_library/               saved code patterns
    ├── macros/
    ├── tasks.db
    ├── audit.db
    ├── scheduler.db
    ├── backups/
    └── piper/                      TTS voice
```

---

## 💬 Try These In v3

**Coder mode (Claude-style):**
```
"Implement a function that batches a list into N-sized chunks"
↳ Searches code_library — if you've done this before, reuses pattern
↳ If new: explores workspace, writes code, runs to verify, saves to library
```

**Ultron mode (plan-then-execute):**
```
"Take a screenshot of my desktop, find the word 'error' on it,
then open a terminal and search Google for that error message"
↳ Generates 3-step plan → executes each → live status in UI
```

**Memory-aware:**
```
"What do you know about my projects?"
↳ Pulls from semantic memories + KG entities
"Remember when we built the login form? Continue from there."
↳ Episodic recall finds the past conversation
```

---

## 🔐 Privacy

- **All models, embeddings, history, memory, code patterns, vector DBs**: on your disk
- **Internet only** for `web_search` (DuckDuckGo) and `search_web_docs`
- **Comm tools** open compose windows — you press send
- **Credential vault** uses OS keyring; values never leave the keychain

---

## ⚠ Honest Limitations (still)

- **1.5b model** can't reliably chain >5 steps even with the planner. Upgrade `LLM_MODEL` in `config.py` to `qwen2.5:7b-instruct` when RAM allows — single biggest improvement.
- **No image generation** (hardware).
- **No always-on wake word in browser** — record button is push-to-talk. The `voice/wake.py` daemon works headlessly though.
- **Hardware constrained** — your 7.5 GB RAM means closing other apps when running 7B+.

---

## 🚧 Deferred / Out-of-Scope For This Session

These were on the wishlist but not built (would need separate sessions):
- **IMAP/SMTP email** (security-sensitive — partial via vault)
- **Telegram bot** (separate deploy story)
- **Docker / SSH** tools (security review needed)
- **Voice cloning** (heavy)
- **Speech translation** (extra deps)
- **Continuous screen recording + retrieval** (disk-heavy)
- **Multi-agent swarm** (planner already gives 80% of the value)

Each is a clean drop-in module if you want to add them later.

---

## 🐛 Troubleshooting

| Problem | Fix |
|---------|-----|
| Frontend says "Loading..." forever | Backend not running. Check `uvicorn` is up on :8000 |
| Tool calls fail | Check `data/audit.db` for errors; test the tool directly |
| `keyring` errors | `sudo apt install gnome-keyring` (or `pass`) |
| Playwright | `python -m playwright install chromium` |
| Ollama disconnected | `ollama serve` |

Issues? Check `journalctl --user -u ultron -f` if running as service.
