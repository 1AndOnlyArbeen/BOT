"""Wake-word listener using openWakeWord (offline). Run as a background daemon.

Uses 'hey jarvis' / 'alexa' / 'hey mycroft' built-in models. After detection, records 6s
and forwards transcription to a callback or to a local HTTP endpoint."""
from __future__ import annotations

import queue
import threading
import time
from typing import Callable

import numpy as np


SAMPLE_RATE = 16000
FRAME_SAMPLES = 1280


def list_models() -> list[str]:
    try:
        import openwakeword
        return list(openwakeword.MODELS.keys())
    except Exception:
        return []


class WakeListener:
    def __init__(
        self,
        wake_words: list[str] | None = None,
        record_seconds: int = 6,
        threshold: float = 0.5,
    ):
        self.wake_words = wake_words or ["hey_jarvis"]
        self.record_seconds = record_seconds
        self.threshold = threshold
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, on_command: Callable[[str], None]) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, args=(on_command,), daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self, on_command: Callable[[str], None]) -> None:
        try:
            import sounddevice as sd
            from openwakeword.model import Model
        except ImportError:
            on_command("[wake] missing deps: pip install openwakeword sounddevice")
            return

        try:
            model = Model(wakeword_models=self.wake_words)
        except Exception as e:
            on_command(f"[wake] model load failed: {e}")
            return

        q: queue.Queue = queue.Queue()

        def cb(indata, frames, t, status):
            q.put(bytes(indata))

        try:
            with sd.RawInputStream(
                samplerate=SAMPLE_RATE, blocksize=FRAME_SAMPLES,
                dtype="int16", channels=1, callback=cb,
            ):
                while not self._stop.is_set():
                    try:
                        chunk = q.get(timeout=0.5)
                    except queue.Empty:
                        continue
                    audio = np.frombuffer(chunk, dtype=np.int16)
                    scores = model.predict(audio)
                    if any(v >= self.threshold for v in scores.values()):
                        text = self._transcribe_after_wake()
                        if text.strip():
                            on_command(text)
                        time.sleep(0.5)
        except Exception as e:
            on_command(f"[wake] stream error: {e}")

    def _transcribe_after_wake(self) -> str:
        try:
            from voice.stt import record_and_transcribe
            return record_and_transcribe(seconds=self.record_seconds)
        except Exception as e:
            return f"[stt error] {e}"
