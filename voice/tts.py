"""Local text-to-speech: Piper (natural) → pyttsx3 (fallback) → espeak (last resort)."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from config import DATA_DIR


_lock = threading.Lock()
PIPER_DIR = DATA_DIR / "piper"
PIPER_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_VOICE = PIPER_DIR / "en_US-amy-medium.onnx"


def _have(c: str) -> bool:
    return shutil.which(c) is not None


def _piper_available() -> bool:
    return _have("piper") and DEFAULT_VOICE.exists()


def _speak_piper(text: str) -> bool:
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = tmp.name
        proc = subprocess.run(
            ["piper", "--model", str(DEFAULT_VOICE), "--output_file", wav_path],
            input=text, text=True, capture_output=True, timeout=30,
        )
        if proc.returncode != 0 or not Path(wav_path).exists():
            return False
        for player in (["paplay", wav_path], ["aplay", "-q", wav_path], ["play", "-q", wav_path]):
            if _have(player[0]):
                subprocess.run(player, capture_output=True, timeout=120)
                Path(wav_path).unlink(missing_ok=True)
                return True
        Path(wav_path).unlink(missing_ok=True)
        return False
    except Exception:
        return False


def _speak_pyttsx3(text: str, rate: int) -> bool:
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", rate)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
        return True
    except Exception:
        return False


def _speak_espeak(text: str, rate: int) -> bool:
    if not _have("espeak"):
        return False
    try:
        subprocess.run(
            ["espeak", "-s", str(rate), text],
            capture_output=True, timeout=120,
        )
        return True
    except Exception:
        return False


def speak(text: str, rate: int = 175) -> None:
    """Block until speech finishes. Tries Piper → pyttsx3 → espeak."""
    text = text.strip()
    if not text:
        return
    with _lock:
        if _piper_available() and _speak_piper(text):
            return
        if _speak_pyttsx3(text, rate):
            return
        _speak_espeak(text, rate)


def speak_async(text: str, rate: int = 175) -> threading.Thread:
    t = threading.Thread(target=speak, args=(text, rate), daemon=True)
    t.start()
    return t


def install_piper_voice() -> str:
    """Download the Amy voice model (~63 MB) for natural TTS. Run once."""
    if DEFAULT_VOICE.exists():
        return f"already installed: {DEFAULT_VOICE}"
    try:
        import requests
    except ImportError:
        return "pip install requests first"
    base = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium"
    files = ["en_US-amy-medium.onnx", "en_US-amy-medium.onnx.json"]
    for fn in files:
        dest = PIPER_DIR / fn
        if dest.exists():
            continue
        r = requests.get(f"{base}/{fn}", timeout=120)
        r.raise_for_status()
        dest.write_bytes(r.content)
    return f"✓ installed Piper voice → {DEFAULT_VOICE}"
