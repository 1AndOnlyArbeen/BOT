"""Central configuration. Edit values here to tune the bot."""
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = DATA_DIR / "documents"
CHROMA_DIR = DATA_DIR / "chroma"
MEMORY_DIR = DATA_DIR / "memory"
DB_PATH = DATA_DIR / "chat.db"
WHISPER_DIR = DATA_DIR / "whisper_models"
WORKSPACE_DIR = BASE_DIR / "workspace"

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

LLM_MODEL = "llama3.2:3b"
EMBED_MODEL = "nomic-embed-text"

LLM_TEMPERATURE = 0.3
LLM_NUM_CTX = 4096
LLM_NUM_PREDICT = 512

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
