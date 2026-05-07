"""Voice: STT (uploaded audio) + TTS."""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from voice.stt import transcribe_file
from voice.tts import speak_async, install_piper_voice

router = APIRouter()


class SpeakBody(BaseModel):
    text: str


@router.post("/stt")
async def stt(audio: UploadFile = File(...)) -> dict:
    suffix = Path(audio.filename or "audio.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await audio.read())
        path = tmp.name
    size = Path(path).stat().st_size
    try:
        text = transcribe_file(path)
        return {"text": text, "bytes": size}
    except Exception as e:
        return {"text": "", "bytes": size, "error": str(e)}
    finally:
        Path(path).unlink(missing_ok=True)


@router.post("/speak")
def speak(body: SpeakBody) -> dict:
    speak_async(body.text)
    return {"ok": True}


@router.post("/install-piper")
def install_piper() -> dict:
    return {"message": install_piper_voice()}
