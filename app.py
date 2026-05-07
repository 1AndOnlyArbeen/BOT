"""Ultron — local Jarvis-style assistant with chat / coder / ultron modes."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from agent.graph import run_agent, stream_agent
from agent.memory import (
    add_message, delete_session, get_messages,
    list_sessions, new_session, rename_session,
)
from agent.file_tools import list_workspace_tree
from agent.learning import all_memories, forget_all, forget_one, remember
from rag.ingest import ingest_uploaded, list_sources, reset_vectorstore
from config import LLM_MODEL, WORKSPACE_DIR, VOICE_AUTO_SUBMIT


st.set_page_config(
    page_title="Ultron",
    page_icon="🦾",
    layout="wide",
    initial_sidebar_state="expanded",
)


CSS = """
<style>
:root {
    --bg: #0d0e12;
    --panel: #14161c;
    --panel2: #1a1d25;
    --border: #2a2e3a;
    --text: #e8eaf0;
    --muted: #8a90a0;
    --accent: #ff3b3b;
    --accent2: #00d4ff;
    --user-bg: #1f2330;
    --code-bg: #0a0b0f;
    --glow: 0 0 12px rgba(255,59,59,0.4);
}
.stApp { background: radial-gradient(ellipse at top, #181a22 0%, var(--bg) 60%); color: var(--text); }
* { color: var(--text); }
[data-testid="stSidebar"] { background: var(--panel); border-right: 1px solid var(--border); }
[data-testid="stSidebar"] > div:first-child { padding-top: 1rem; }
[data-testid="stHeader"] { background: transparent; }

.block-container { padding-top: 1.5rem !important; padding-bottom: 6rem !important; }

[data-testid="stChatMessage"] {
    background: transparent !important; border: none !important;
    padding: 0.5rem 0 !important; margin-bottom: 1rem;
}
[data-testid="stChatMessage"][data-testid*="user"] {
    background: var(--user-bg) !important; border-radius: 14px !important;
    padding: 0.75rem 1.1rem !important; margin-left: 3rem;
    border: 1px solid var(--border);
}
[data-testid="stChatMessageContent"] p { color: var(--text); line-height: 1.65; margin-bottom: 0.6rem; }
[data-testid="stChatMessage"] code {
    background: var(--code-bg); color: var(--accent2);
    padding: 2px 6px; border-radius: 4px; font-size: 0.92em;
    border: 1px solid var(--border);
}
[data-testid="stChatMessage"] pre {
    background: var(--code-bg) !important; border-radius: 10px;
    padding: 1rem !important; border: 1px solid var(--border);
}
[data-testid="stChatMessage"] pre code { color: #f0f0f0; background: transparent; border: none; }

[data-testid="stChatInput"] {
    background: var(--panel2); border: 1px solid var(--border);
    border-radius: 16px; box-shadow: 0 4px 18px rgba(0,0,0,0.3);
}
[data-testid="stChatInput"] textarea { color: var(--text) !important; }

div.stButton > button {
    background: var(--panel2); color: var(--text);
    border: 1px solid var(--border); border-radius: 10px;
    font-weight: 500; transition: all 0.15s;
}
div.stButton > button:hover {
    background: var(--user-bg); border-color: var(--accent);
    color: var(--accent);
}
div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--accent), #c92020);
    color: white; border: none; box-shadow: var(--glow);
}
div.stButton > button[kind="primary"]:hover {
    filter: brightness(1.1); box-shadow: 0 0 20px rgba(255,59,59,0.6);
}

[data-testid="stFileUploader"] {
    background: var(--panel2); border: 1px dashed var(--border);
    border-radius: 10px;
}
[data-testid="stFileUploader"] section { color: var(--muted); }
[data-testid="stFileUploaderDropzoneInstructions"] { color: var(--muted) !important; }

input, textarea, select {
    background: var(--panel2) !important; color: var(--text) !important;
    border-color: var(--border) !important;
}

h1, h2, h3 { color: var(--text); font-weight: 600; }

.brand {
    font-family: 'Courier New', monospace;
    font-size: 1.3rem; font-weight: 700;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: 0.15em; margin: 0.5rem 0;
}
.tagline { color: var(--muted); font-size: 0.75rem; letter-spacing: 0.05em; }
.sidebar-section {
    font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em;
    color: var(--muted); margin: 1.2rem 0 0.5rem 0; font-weight: 600;
}
.welcome { text-align: center; color: var(--muted); padding: 4rem 1rem; }
.welcome h1 {
    font-size: 2.5rem; color: var(--text); margin-bottom: 0.5rem;
    font-family: 'Courier New', monospace; letter-spacing: 0.1em;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.welcome p { font-size: 1rem; color: var(--muted); }

.badge {
    display: inline-block; background: var(--user-bg); color: var(--accent2);
    padding: 2px 10px; border-radius: 999px; font-size: 0.7rem;
    margin-right: 6px; border: 1px solid var(--border);
}

.editor-header {
    background: #000; color: var(--accent2);
    padding: 0.5rem 1rem; border-radius: 10px 10px 0 0;
    font-family: monospace; font-size: 0.85rem;
    border: 1px solid var(--border); border-bottom: none;
}

.memory-card {
    background: var(--panel2); border: 1px solid var(--border);
    padding: 0.5rem 0.75rem; border-radius: 8px;
    margin-bottom: 0.4rem; font-size: 0.85rem;
    color: var(--text); border-left: 3px solid var(--accent2);
}

hr { border-color: var(--border) !important; margin: 0.75rem 0 !important; }
#MainMenu, footer { visibility: hidden; }

.pulse {
    display: inline-block; width: 8px; height: 8px;
    background: var(--accent); border-radius: 50%;
    animation: pulse 1.5s infinite;
    margin-right: 6px;
}
@keyframes pulse {
    0%, 100% { opacity: 1; box-shadow: 0 0 8px var(--accent); }
    50% { opacity: 0.4; box-shadow: 0 0 2px var(--accent); }
}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)


if "session_id" not in st.session_state:
    sessions = list_sessions()
    st.session_state.session_id = sessions[0]["id"] if sessions else new_session("New chat")
if "mode" not in st.session_state:
    st.session_state.mode = "ultron"
if "current_file" not in st.session_state:
    st.session_state.current_file = None
if "voice_pending" not in st.session_state:
    st.session_state.voice_pending = None


def _auto_title(text: str) -> str:
    t = text.strip().split("\n")[0]
    return (t[:40] + "…") if len(t) > 40 else t


def _lang_for(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".tsx": "tsx", ".jsx": "jsx", ".html": "html", ".css": "css",
        ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".md": "markdown",
        ".sh": "bash", ".sql": "sql", ".go": "go", ".rs": "rust",
    }.get(ext, "text")


with st.sidebar:
    st.markdown(
        '<div class="brand">🦾 ULTRON</div>'
        '<div class="tagline">LOCAL · OFFLINE · YOURS</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<span class="badge">{LLM_MODEL}</span><span class="badge">●</span>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sidebar-section">Mode</div>', unsafe_allow_html=True)
    mode = st.radio(
        "mode",
        ["ultron", "chat", "coder"],
        label_visibility="collapsed",
        format_func=lambda m: {"ultron": "🦾 Ultron (system)", "chat": "💬 Chat (RAG)", "coder": "💻 Coder"}[m],
        index=["ultron", "chat", "coder"].index(st.session_state.mode),
    )
    if mode != st.session_state.mode:
        st.session_state.mode = mode
        st.rerun()

    if st.button("✨ New chat", use_container_width=True, type="primary"):
        st.session_state.session_id = new_session("New chat")
        st.rerun()

    st.markdown('<div class="sidebar-section">Recent</div>', unsafe_allow_html=True)
    for s in list_sessions()[:25]:
        cols = st.columns([5, 1])
        active = s["id"] == st.session_state.session_id
        label = s["title"][:26] + ("…" if len(s["title"]) > 26 else "")
        if cols[0].button(
            label, key=f"sess_{s['id']}", use_container_width=True,
            type="primary" if active else "secondary",
        ):
            st.session_state.session_id = s["id"]
            st.rerun()
        if cols[1].button("×", key=f"del_{s['id']}"):
            delete_session(s["id"])
            sessions = list_sessions()
            st.session_state.session_id = sessions[0]["id"] if sessions else new_session("New chat")
            st.rerun()

    if st.session_state.mode == "chat":
        st.markdown('<div class="sidebar-section">Documents</div>', unsafe_allow_html=True)
        uploaded = st.file_uploader(
            "Drop files",
            type=["pdf", "docx", "txt", "md"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )
        if uploaded and st.button("📥 Ingest", use_container_width=True):
            with st.spinner("Embedding…"):
                n = ingest_uploaded(uploaded)
            st.success(f"+{n} chunks")
        sources = list_sources()
        if sources:
            with st.expander(f"📚 {len(sources)} indexed"):
                for s in sources:
                    st.caption(f"• {s}")
            if st.button("Clear KB", use_container_width=True):
                reset_vectorstore()
                st.rerun()

    if st.session_state.mode == "coder":
        st.markdown('<div class="sidebar-section">Workspace</div>', unsafe_allow_html=True)
        tree = list_workspace_tree(max_depth=3)
        if not tree:
            st.caption("(empty)")
        else:
            for rel, is_dir in tree:
                indent = "&nbsp;&nbsp;" * (rel.count("/"))
                if is_dir:
                    st.markdown(f"{indent}📁 {Path(rel).name}/", unsafe_allow_html=True)
                else:
                    if st.button(
                        f"📄 {Path(rel).name}",
                        key=f"f_{rel}", use_container_width=True,
                    ):
                        st.session_state.current_file = rel
                        st.rerun()

    st.markdown('<div class="sidebar-section">Memory</div>', unsafe_allow_html=True)
    mems = all_memories()
    st.caption(f"{len(mems)} learned facts")
    if mems:
        with st.expander("🧠 What I know"):
            for m in mems[:50]:
                cols = st.columns([6, 1])
                cols[0].markdown(
                    f'<div class="memory-card">{m["text"]}</div>',
                    unsafe_allow_html=True,
                )
                if cols[1].button("×", key=f"forg_{hash(m['text'])}"):
                    forget_one(m["text"])
                    st.rerun()
        if st.button("Forget all", use_container_width=True):
            forget_all()
            st.rerun()
    new_mem = st.text_input("Teach me", placeholder="User likes dark mode", key="new_mem_input")
    if new_mem and st.button("➕ Save", use_container_width=True):
        remember([new_mem])
        st.rerun()

    st.markdown('<div class="sidebar-section">Voice</div>', unsafe_allow_html=True)
    voice_in = st.toggle("🎤 Voice input", value=False)
    voice_out = st.toggle("🔊 Voice output", value=st.session_state.mode == "ultron")
    auto_submit = st.toggle("⚡ Auto-submit voice", value=VOICE_AUTO_SUBMIT)
    record_seconds = st.slider("Seconds", 3, 20, 8) if voice_in else 8

    with st.expander("Voice setup"):
        from pathlib import Path as _P
        from config import DATA_DIR as _DD
        piper_voice = _DD / "piper" / "en_US-amy-medium.onnx"
        if not piper_voice.exists():
            if st.button("🔉 Install Piper natural voice (~63 MB)", use_container_width=True):
                from voice.tts import install_piper_voice
                with st.spinner("Downloading…"):
                    msg = install_piper_voice()
                st.caption(msg)
        else:
            st.caption("✓ Piper voice installed")


def _handle(prompt: str):
    if not get_messages(st.session_state.session_id):
        rename_session(st.session_state.session_id, _auto_title(prompt))

    add_message(st.session_state.session_id, "user", prompt)
    with st.chat_message("user", avatar="🧑"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🦾"):
        status_box = st.empty()
        text_box = st.empty()
        history = get_messages(st.session_state.session_id)[:-1]
        reply = ""
        tool_calls = []
        router_info = None
        try:
            for ev in stream_agent(prompt, history=history, mode=st.session_state.mode):
                t = ev["type"]
                if t == "router":
                    router_info = ev["data"]
                    cats = ", ".join(router_info["categories"]) or "default"
                    status_box.caption(f"🧭 routed → {cats} ({router_info['tool_count']} tools)")
                elif t == "tool_call":
                    tool_calls.append(ev["data"])
                    status_box.caption(f"🔧 calling: {ev['data']['name']}({ev['data']['args'][:80]})")
                elif t == "tool_result":
                    status_box.caption(f"← {ev['data']['name']}: {ev['data']['content'][:100]}")
                elif t == "token":
                    reply = ev["data"]
                    text_box.markdown(reply)
                elif t == "final":
                    reply = ev["data"] or reply
                    text_box.markdown(reply)
                elif t == "error":
                    reply = f"⚠️ {ev['data']}"
                    text_box.markdown(reply)
        except Exception as e:
            reply = f"⚠️ {type(e).__name__}: {e}"
            text_box.markdown(reply)

        if tool_calls:
            with st.expander(f"🛠 {len(tool_calls)} tool call(s)"):
                for tc in tool_calls:
                    st.caption(f"• {tc['name']}({tc['args']})")
        status_box.empty()

    add_message(st.session_state.session_id, "assistant", reply)

    if voice_out and reply and not reply.startswith("⚠️"):
        try:
            from voice.tts import speak_async
            speak_async(reply)
        except Exception as e:
            st.caption(f"(TTS failed: {e})")


def _render_chat_panel():
    messages = get_messages(st.session_state.session_id)
    if not messages:
        welcome = {
            "ultron": ("🦾 ULTRON ONLINE", "Voice or type. I'll search, message, code, control your laptop."),
            "chat": ("Knowledge Mode", "Ask anything — I'll search your docs, the web, run code."),
            "coder": ("Coder Mode", "I can browse <code>workspace/</code>, read & edit files, run code."),
        }[st.session_state.mode]
        st.markdown(
            f'<div class="welcome"><h1>{welcome[0]}</h1><p>{welcome[1]}</p></div>',
            unsafe_allow_html=True,
        )

    for m in messages:
        with st.chat_message(m["role"], avatar="🧑" if m["role"] == "user" else "🦾"):
            st.markdown(m["content"])


def _render_editor_panel():
    cf = st.session_state.current_file
    if not cf:
        st.markdown(
            '<div class="welcome" style="padding:2rem 1rem;">'
            '<p>📂 Select a file or ask Ultron to create one.</p></div>',
            unsafe_allow_html=True,
        )
        return

    full = WORKSPACE_DIR / cf
    if not full.exists():
        st.session_state.current_file = None
        st.warning(f"{cf} no longer exists")
        return

    st.markdown(f'<div class="editor-header">📄 {cf}</div>', unsafe_allow_html=True)

    try:
        content = full.read_text(encoding="utf-8")
    except Exception as e:
        st.error(f"Cannot read: {e}")
        return

    edit_key = f"edit_{cf}"
    edited = st.text_area(
        "editor", value=content, height=420,
        key=edit_key, label_visibility="collapsed",
    )

    cols = st.columns([1, 1, 1, 3])
    if cols[0].button("💾 Save", use_container_width=True, type="primary"):
        full.write_text(edited, encoding="utf-8")
        st.success("Saved")
    if cols[1].button("↻ Reload", use_container_width=True):
        st.rerun()
    if full.suffix == ".py":
        if cols[2].button("▶ Run", use_container_width=True):
            import subprocess
            try:
                r = subprocess.run(
                    ["python3", str(full)], capture_output=True, text=True,
                    timeout=30, cwd=str(WORKSPACE_DIR),
                )
                with st.expander("Output", expanded=True):
                    if r.stdout:
                        st.code(r.stdout, language="text")
                    if r.stderr:
                        st.code(r.stderr, language="text")
                    st.caption(f"exit {r.returncode}")
            except subprocess.TimeoutExpired:
                st.error("Timeout (30s)")

    with st.expander("👁 Preview", expanded=False):
        st.code(edited, language=_lang_for(cf))


if st.session_state.mode == "coder":
    left, right = st.columns([1, 1], gap="medium")
    with left:
        _render_chat_panel()
    with right:
        _render_editor_panel()
else:
    _render_chat_panel()


if voice_in:
    cols = st.columns([1, 4])
    if cols[0].button(f"🎤 {record_seconds}s", use_container_width=True, type="primary"):
        with st.spinner("🔴 Listening…"):
            try:
                from voice.stt import record_and_transcribe
                spoken = record_and_transcribe(seconds=record_seconds)
            except Exception as e:
                st.error(f"Mic/STT error: {e}")
                spoken = ""
        if spoken:
            if auto_submit:
                _handle(spoken)
                st.rerun()
            else:
                st.session_state.voice_pending = spoken
                st.rerun()
    if st.session_state.voice_pending:
        cols[1].info(f"🗣 {st.session_state.voice_pending}")
        c1, c2 = cols[1].columns(2)
        if c1.button("Send", use_container_width=True, type="primary"):
            txt = st.session_state.voice_pending
            st.session_state.voice_pending = None
            _handle(txt)
            st.rerun()
        if c2.button("Discard", use_container_width=True):
            st.session_state.voice_pending = None
            st.rerun()


placeholder = {
    "ultron": "Tell Ultron what to do…",
    "chat": "Ask Ultron anything…",
    "coder": "Build, fix, or explain code…",
}[st.session_state.mode]
prompt = st.chat_input(placeholder)
if prompt:
    _handle(prompt)
    st.rerun()
