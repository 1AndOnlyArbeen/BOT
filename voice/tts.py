"""Local text-to-speech: Piper (natural) → pyttsx3 (fallback) → espeak (last resort).

Voice profiles tune the output. The "ultron" profile uses a deeper male voice
(en_US-ryan-high) and pipes the wav through ffmpeg for pitch-down + reverb to
sound more like the film's AI villain. Config: VOICE_PROFILE in config.py.
"""
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


def _resolve_piper_bin() -> str | None:
    """Return the Rhasspy Piper TTS binary, NOT the unrelated /usr/bin/piper GTK app.

    Priority:
      1. Python venv's `bin/piper` (installed by `pip install piper-tts`) — this
         is the real TTS engine.
      2. `python -m piper` — fallback for editable installs.
      3. Any system `piper` whose --help mentions "MODEL" (i.e. accepts -m flag).
    """
    import sys
    # 1) venv binary
    venv_bin = Path(sys.executable).parent / "piper"
    if venv_bin.exists() and venv_bin.is_file():
        return str(venv_bin)
    # 2) module form
    try:
        import piper as _piper_mod  # type: ignore
        return f"{sys.executable} -m piper"
    except ImportError:
        pass
    # 3) any other piper that looks like the TTS one
    for cand in shutil.which("piper") or "", "/usr/local/bin/piper":
        if cand and Path(cand).exists():
            try:
                r = subprocess.run([cand, "--help"], capture_output=True, text=True, timeout=5)
                if "MODEL" in (r.stdout + r.stderr):
                    return cand
            except Exception:
                pass
    return None


_PIPER_BIN: str | None = _resolve_piper_bin()


# voice_id → (huggingface path, [files to download])
PIPER_VOICES = {
    "amy": ("en/en_US/amy/medium", ["en_US-amy-medium.onnx", "en_US-amy-medium.onnx.json"]),
    "ryan": ("en/en_US/ryan/high", ["en_US-ryan-high.onnx", "en_US-ryan-high.onnx.json"]),
    "lessac": ("en/en_US/lessac/medium", ["en_US-lessac-medium.onnx", "en_US-lessac-medium.onnx.json"]),
    "joe": ("en/en_US/joe/medium", ["en_US-joe-medium.onnx", "en_US-joe-medium.onnx.json"]),
    "alan_gb": ("en/en_GB/alan/medium", ["en_GB-alan-medium.onnx", "en_GB-alan-medium.onnx.json"]),
}


# Per-profile defaults. FFmpeg filter strings target the playback wav.
VOICE_PROFILES = {
    "default": {
        "voice": "amy",
        "ffmpeg_filter": None,
        "rate_scale": 1.0,
    },
    "ultron": {
        # Ryan is a deeper male voice. asetrate pitches down + slows; atempo
        # restores tempo without raising pitch. EQ adds presence so consonants
        # cut through the reverb. Compressor + volume gain push perceived
        # loudness without clipping.
        "voice": "ryan",
        "ffmpeg_filter": (
            "asetrate=22050*0.88,"                                   # pitch-down
            "atempo=1.1364,"                                         # 1/0.88, restores tempo
            "highpass=f=90,"                                         # cut sub-bass rumble
            "equalizer=f=2800:t=q:w=1.4:g=6,"                        # strong presence boost
            "equalizer=f=5500:t=q:w=2:g=3,"                          # air/sparkle for clarity
            "aecho=0.5:0.18:55:0.15,"                                # very subtle, dry echo
            "acompressor=threshold=0.08:ratio=4:attack=15:release=180,"
            "volume=3.8,"                                            # heavy gain
            "alimiter=limit=0.97"                                    # ceiling to prevent clipping
        ),
        "rate_scale": 0.95,
    },
}


# Active profile name. Initialized from config but mutable at runtime via
# set_active_profile() so users can switch voices without editing config.py.
try:
    from config import VOICE_PROFILE as _CONFIG_PROFILE
except ImportError:
    _CONFIG_PROFILE = "default"
_active_profile_name: str = _CONFIG_PROFILE or "default"


def get_active_profile() -> str:
    return _active_profile_name


def set_active_profile(name: str) -> bool:
    """Switch the active voice profile at runtime. Returns True if applied."""
    global _active_profile_name
    if name not in VOICE_PROFILES:
        return False
    _active_profile_name = name
    return True


def list_profiles() -> list[str]:
    return list(VOICE_PROFILES.keys())


def _profile() -> dict:
    """Active voice profile (falls back to default)."""
    return VOICE_PROFILES.get(_active_profile_name, VOICE_PROFILES["default"])


def _voice_model() -> Path:
    """Path to the .onnx file for the active profile, or the legacy Amy default."""
    p = _profile()
    voice_id = p.get("voice", "amy")
    files = PIPER_VOICES.get(voice_id, PIPER_VOICES["amy"])[1]
    return PIPER_DIR / files[0]


# Backwards-compat constant some callers reference.
DEFAULT_VOICE = _voice_model()


def _have(c: str) -> bool:
    return shutil.which(c) is not None


def _piper_available() -> bool:
    return _PIPER_BIN is not None and _voice_model().exists()


def _piper_cmd(model_path: str, out_path: str) -> list[str]:
    """Build the piper invocation. Handles both binary and `python -m piper` forms."""
    if _PIPER_BIN and " -m " in _PIPER_BIN:
        # "python -m piper" form
        return _PIPER_BIN.split() + ["--model", model_path, "--output_file", out_path]
    return [_PIPER_BIN, "--model", model_path, "--output_file", out_path]


def _apply_ffmpeg_fx(in_wav: str, ffmpeg_filter: str) -> str | None:
    """Pipe in_wav through ffmpeg with the given filter, return the new wav path."""
    if not _have("ffmpeg") or not ffmpeg_filter:
        return None
    out_wav = in_wav + ".fx.wav"
    try:
        proc = subprocess.run(
            ["ffmpeg", "-y", "-i", in_wav, "-af", ffmpeg_filter, out_wav],
            capture_output=True, timeout=30,
        )
        if proc.returncode != 0 or not Path(out_wav).exists():
            return None
        return out_wav
    except Exception:
        return None


def _play_wav(wav_path: str) -> bool:
    for player in (["paplay", wav_path], ["aplay", "-q", wav_path], ["play", "-q", wav_path]):
        if _have(player[0]):
            try:
                subprocess.run(player, capture_output=True, timeout=120)
                return True
            except Exception:
                return False
    return False


class SpeechHandle:
    """Returned by speak_interruptible() — call .stop() to cut playback short."""
    def __init__(self) -> None:
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()
        self._stopped = False
        self._tmp_paths: list[str] = []

    def attach(self, proc: subprocess.Popen) -> None:
        with self._lock:
            self._proc = proc

    def add_tmp(self, path: str) -> None:
        self._tmp_paths.append(path)

    def stop(self) -> None:
        with self._lock:
            self._stopped = True
            if self._proc and self._proc.poll() is None:
                try:
                    self._proc.terminate()
                except Exception:
                    pass

    def is_stopped(self) -> bool:
        with self._lock:
            return self._stopped

    def wait(self) -> None:
        with self._lock:
            proc = self._proc
        if proc is not None:
            try:
                proc.wait()
            except Exception:
                pass
        for p in self._tmp_paths:
            Path(p).unlink(missing_ok=True)


def _play_wav_interruptible(wav_path: str, handle: SpeechHandle) -> bool:
    """Play a wav with subprocess.Popen so the handle can kill it mid-play."""
    for player_args in (["paplay", wav_path], ["aplay", "-q", wav_path], ["play", "-q", wav_path]):
        if _have(player_args[0]):
            try:
                proc = subprocess.Popen(
                    player_args,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                handle.attach(proc)
                proc.wait()
                return not handle.is_stopped()
            except Exception:
                return False
    return False


def _speak_piper(text: str) -> bool:
    profile = _profile()
    voice = _voice_model()
    if not voice.exists() or _PIPER_BIN is None:
        return False
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = tmp.name
        proc = subprocess.run(
            _piper_cmd(str(voice), wav_path),
            input=text, text=True, capture_output=True, timeout=30,
        )
        if proc.returncode != 0 or not Path(wav_path).exists():
            Path(wav_path).unlink(missing_ok=True)
            return False

        play_wav = wav_path
        fx = profile.get("ffmpeg_filter")
        if fx:
            fx_wav = _apply_ffmpeg_fx(wav_path, fx)
            if fx_wav:
                play_wav = fx_wav

        ok = _play_wav(play_wav)
        Path(wav_path).unlink(missing_ok=True)
        if play_wav != wav_path:
            Path(play_wav).unlink(missing_ok=True)
        return ok
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
        # Lower pitch + slightly slower for more "AI villain" feel even on espeak.
        subprocess.run(
            ["espeak", "-s", str(int(rate * 0.9)), "-p", "30", text],
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


def speak_interruptible(text: str) -> SpeechHandle:
    """Speak in a background thread; return a handle whose .stop() kills playback.

    Uses Piper (with FX if profile asks) → falls back to espeak. Skips pyttsx3
    in this path because it's not interruptible from outside.
    """
    handle = SpeechHandle()
    text = (text or "").strip()
    if not text:
        return handle

    def _worker():
        with _lock:
            if handle.is_stopped():
                return
            # Piper path
            if _piper_available():
                profile = _profile()
                voice = _voice_model()
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    wav_path = tmp.name
                try:
                    proc = subprocess.run(
                        _piper_cmd(str(voice), wav_path),
                        input=text, text=True, capture_output=True, timeout=30,
                    )
                    if proc.returncode != 0 or not Path(wav_path).exists():
                        Path(wav_path).unlink(missing_ok=True)
                    else:
                        play_wav = wav_path
                        handle.add_tmp(wav_path)
                        fx = profile.get("ffmpeg_filter")
                        if fx:
                            fx_wav = _apply_ffmpeg_fx(wav_path, fx)
                            if fx_wav:
                                play_wav = fx_wav
                                handle.add_tmp(fx_wav)
                        if not handle.is_stopped():
                            _play_wav_interruptible(play_wav, handle)
                        return
                except Exception:
                    Path(wav_path).unlink(missing_ok=True)
            # espeak fallback
            if _have("espeak") and not handle.is_stopped():
                try:
                    proc = subprocess.Popen(
                        ["espeak", "-s", "157", "-p", "30", text],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
                    handle.attach(proc)
                    proc.wait()
                except Exception:
                    pass

    threading.Thread(target=_worker, daemon=True).start()
    return handle


def install_piper_voice(voice_id: str | None = None) -> str:
    """Download a Piper voice. voice_id matches a key in PIPER_VOICES.
    Defaults to whatever the active profile needs."""
    if voice_id is None:
        voice_id = _profile().get("voice", "amy")
    if voice_id not in PIPER_VOICES:
        return f"unknown voice '{voice_id}'. options: {', '.join(PIPER_VOICES)}"
    try:
        import requests
    except ImportError:
        return "pip install requests first"

    rel, files = PIPER_VOICES[voice_id]
    base = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{rel}"
    target_onnx = PIPER_DIR / files[0]
    if target_onnx.exists():
        return f"already installed: {target_onnx}"

    for fn in files:
        dest = PIPER_DIR / fn
        if dest.exists():
            continue
        r = requests.get(f"{base}/{fn}", timeout=180)
        r.raise_for_status()
        dest.write_bytes(r.content)
    return f"✓ installed Piper voice '{voice_id}' → {target_onnx}"
