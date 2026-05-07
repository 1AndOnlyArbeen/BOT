"""Local speech-to-text using faster-whisper. Auto-sizes model to free RAM."""
from __future__ import annotations

import tempfile
from functools import lru_cache
from pathlib import Path

import numpy as np

from config import WHISPER_MODEL_SIZE, WHISPER_COMPUTE_TYPE, WHISPER_DIR


def _free_gb() -> float:
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) / 1024 / 1024
    except Exception:
        pass
    return 0.0


def _autosize() -> str:
    """Pick a Whisper model that fits available RAM."""
    free = _free_gb()
    if free >= 6: return "small"
    if free >= 3: return "base"
    return "tiny"


def _resolve_size() -> str:
    if WHISPER_MODEL_SIZE.lower() == "auto":
        return _autosize()
    return WHISPER_MODEL_SIZE


@lru_cache(maxsize=1)
def _model():
    from faster_whisper import WhisperModel
    return WhisperModel(
        _resolve_size(),
        device="cpu",
        compute_type=WHISPER_COMPUTE_TYPE,
        download_root=str(WHISPER_DIR),
    )


def transcribe_file(path: str | Path) -> str:
    segments, _ = _model().transcribe(str(path), beam_size=1, vad_filter=True)
    return " ".join(s.text.strip() for s in segments).strip()


def transcribe_bytes(audio_bytes: bytes, suffix: str = ".wav") -> str:
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        return transcribe_file(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def record_and_transcribe(seconds: int = 8) -> str:
    """Record from default mic, then transcribe."""
    import sounddevice as sd
    from scipy.io import wavfile

    from config import VOICE_SAMPLE_RATE

    audio = sd.rec(
        int(seconds * VOICE_SAMPLE_RATE),
        samplerate=VOICE_SAMPLE_RATE,
        channels=1,
        dtype="int16",
    )
    sd.wait()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wavfile.write(tmp.name, VOICE_SAMPLE_RATE, audio)
        path = tmp.name
    try:
        return transcribe_file(path)
    finally:
        Path(path).unlink(missing_ok=True)
