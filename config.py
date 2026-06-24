"""Central configuration. Edit values here to tune the bot."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = DATA_DIR / "documents"
CHROMA_DIR = DATA_DIR / "chroma"
MEMORY_DIR = DATA_DIR / "memory"
DB_PATH = DATA_DIR / "chat.db"
WHISPER_DIR = DATA_DIR / "whisper_models"


def _resolve_workspace() -> Path:
    """Pick where file_tools should write.

    Priority:
      1. $BOT_WORKDIR env var if set (explicit override).
      2. Current working directory if it's OUTSIDE the BOT codebase
         (user `cd`'d into their project before launching the CLI — write there).
      3. BASE_DIR / 'workspace' fallback (user launched from inside BOT, or via
         run.sh which cd's into BOT — keep legacy behavior so we don't pollute
         the bot's own source tree).
    """
    explicit = os.environ.get("BOT_WORKDIR", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    try:
        cwd = Path(os.getcwd()).resolve()
    except (OSError, FileNotFoundError):
        return (BASE_DIR / "workspace").resolve()
    base = BASE_DIR.resolve()
    if str(cwd).startswith(str(base)):
        return base / "workspace"
    return cwd


WORKSPACE_DIR = _resolve_workspace()

for p in (DATA_DIR, DOCS_DIR, CHROMA_DIR, MEMORY_DIR, WHISPER_DIR, WORKSPACE_DIR):
    p.mkdir(parents=True, exist_ok=True)

MEMORY_TOP_K = 5
MEMORY_AUTO_LEARN = True

VOICE_AUTO_SUBMIT = True
VOICE_PROFILE = "ultron"  # "default" (Amy) or "ultron" (deep male + FX)

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".scss",
    ".json", ".yaml", ".yml", ".md", ".txt", ".sh", ".sql",
    ".go", ".rs", ".java", ".cpp", ".c", ".h", ".rb", ".php",
}

LLM_MODEL = "llama3.1:8b"
EMBED_MODEL = "nomic-embed-text"

LLM_TEMPERATURE = 0.3
LLM_NUM_CTX = 8192         # context window — pushed to llama3.2:3b's safe local-CPU max
                           # so memory + RAG + workspace primer + history all fit comfortably
LLM_NUM_PREDICT = 1800     # max output tokens — high so responses feel detailed like Claude
                           # (3B model may sometimes drift on long outputs; lower to 800 if quality drops)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
RETRIEVE_K = 4

WHISPER_MODEL_SIZE = "auto"
WHISPER_COMPUTE_TYPE = "int8"

WAKE_WORDS = ["hey_jarvis"]
WAKE_THRESHOLD = 0.5

VOICE_SAMPLE_RATE = 16000
VOICE_MAX_SECONDS = 30

WEB_SEARCH_RESULTS = 5
