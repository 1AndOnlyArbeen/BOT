"""Document generation: PDF, markdown rendering, text→speech file."""
from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from langchain_core.tools import tool


OUT_DIR = Path.home() / "Documents" / "Ultron"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _have(c: str) -> bool:
    return shutil.which(c) is not None


@tool
def make_pdf(content: str, filename: str = "") -> str:
    """Create a PDF from plain text or markdown content. Saved to ~/Documents/Ultron/."""
    if not filename:
        filename = f"doc_{int(time.time())}.pdf"
    if not filename.endswith(".pdf"):
        filename += ".pdf"
    out = OUT_DIR / filename

    if _have("pandoc"):
        try:
            p = subprocess.run(
                ["pandoc", "-f", "markdown", "-o", str(out)],
                input=content, text=True,
                capture_output=True, timeout=30,
            )
            if out.exists():
                return f"✓ {out}"
            return f"[error] pandoc: {p.stderr}"
        except Exception as e:
            pass

    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
    except ImportError:
        return "[error] install pandoc or pip install reportlab"

    c = canvas.Canvas(str(out), pagesize=A4)
    width, height = A4
    y = height - 50
    for line in content.split("\n"):
        if y < 50:
            c.showPage()
            y = height - 50
        c.drawString(40, y, line[:110])
        y -= 14
    c.save()
    return f"✓ {out}"


@tool
def text_to_speech_file(text: str, filename: str = "") -> str:
    """Convert text to an audio file (.wav) via espeak."""
    if not _have("espeak"):
        return "[error] install espeak"
    if not filename:
        filename = f"tts_{int(time.time())}.wav"
    if not filename.endswith(".wav"):
        filename += ".wav"
    out = OUT_DIR / filename
    try:
        subprocess.run(
            ["espeak", "-w", str(out), text],
            timeout=60, capture_output=True,
        )
        return f"✓ {out}"
    except Exception as e:
        return f"[error] {e}"


@tool
def markdown_to_html(content: str, filename: str = "") -> str:
    """Render markdown to HTML file."""
    try:
        import markdown as md
    except ImportError:
        return "[error] pip install markdown"
    html = (
        "<!doctype html><meta charset='utf-8'>"
        "<style>body{font-family:system-ui;max-width:760px;margin:2em auto;padding:0 1em;line-height:1.6}"
        "code{background:#f4f4f4;padding:2px 6px;border-radius:3px}pre{background:#f4f4f4;padding:1em;border-radius:6px;overflow:auto}</style>"
        + md.markdown(content, extensions=["fenced_code", "tables"])
    )
    if not filename:
        filename = f"doc_{int(time.time())}.html"
    if not filename.endswith(".html"):
        filename += ".html"
    out = OUT_DIR / filename
    out.write_text(html, encoding="utf-8")
    return f"✓ {out}"


DOCUMENT_TOOLS = [make_pdf, text_to_speech_file, markdown_to_html]
