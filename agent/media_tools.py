"""Media: download YouTube/audio, get info, record audio."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from langchain_core.tools import tool


DOWNLOAD_DIR = Path.home() / "Downloads" / "Ultron"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _have(c: str) -> bool:
    return shutil.which(c) is not None


@tool
def youtube_download(url: str, audio_only: bool = False) -> str:
    """Download a YouTube/SoundCloud/etc video or audio via yt-dlp."""
    if not _have("yt-dlp"):
        return "[error] install yt-dlp (pip install yt-dlp)"
    out_template = str(DOWNLOAD_DIR / "%(title)s.%(ext)s")
    args = ["yt-dlp", "-o", out_template]
    if audio_only:
        args += ["-x", "--audio-format", "mp3"]
    args.append(url)
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=600)
        tail = "\n".join(r.stdout.split("\n")[-15:])
        return tail + (f"\n[errors]\n{r.stderr[-500:]}" if r.returncode else f"\n✓ saved to {DOWNLOAD_DIR}")
    except subprocess.TimeoutExpired:
        return "[timeout] download exceeded 10 min"


@tool
def youtube_info(url: str) -> str:
    """Get title/duration/uploader of a YouTube video without downloading."""
    if not _have("yt-dlp"):
        return "[error] install yt-dlp"
    try:
        r = subprocess.run(
            ["yt-dlp", "--print", "%(title)s | %(uploader)s | %(duration_string)s | %(view_count)s views", url],
            capture_output=True, text=True, timeout=30,
        )
        return r.stdout.strip() or r.stderr.strip()
    except Exception as e:
        return f"[error] {e}"


@tool
def record_audio(seconds: int = 10, filename: str = "") -> str:
    """Record audio from default mic to ~/Downloads/Ultron/."""
    if not filename:
        import time
        filename = f"recording_{int(time.time())}.wav"
    if not filename.endswith(".wav"):
        filename += ".wav"
    out = DOWNLOAD_DIR / filename

    if _have("arecord"):
        try:
            subprocess.run(
                ["arecord", "-d", str(seconds), "-f", "cd", str(out)],
                capture_output=True, timeout=seconds + 5,
            )
            return f"✓ recorded {seconds}s to {out}"
        except Exception as e:
            return f"[error] {e}"
    return "[error] arecord not available"


MEDIA_TOOLS = [youtube_download, youtube_info, record_audio]
