"""Always-on voice loop — Ultron's Jarvis-style voice mode.

Cycle:
  wake ("ultron") → greet ("boss, how can i help you?") → record command →
  transcribe → run agent → speak reply → wait for next wake.

Three wake-detection backends, picked in order:
  - **keyword** (default, no extra deps): continuously transcribes short audio
    chunks with VAD and triggers when the configured wake word ("ultron") is
    heard. Works for ANY wake phrase but uses CPU.
  - **openwakeword**: dedicated wake-word model. Faster but only supports
    built-in phrases (hey_jarvis, alexa, hey_mycroft).
  - **ptt**: press Enter to talk. No mic listening at all — last-resort fallback.
"""
from __future__ import annotations

import os
import queue
import re
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from rich.console import Console

from config import VOICE_SAMPLE_RATE, WAKE_WORDS, WAKE_THRESHOLD


@dataclass
class VoiceConfig:
    wake_words: tuple[str, ...] = ("ultron",)
    greeting: str = "Boss, how can I help?"
    record_seconds: int = 6
    chunk_seconds: float = 2.0
    speak_replies: bool = True
    speak_max_chars: int = 800
    wake_threshold: float = WAKE_THRESHOLD
    command_timeout_sec: float = 8.0  # drop awaiting_command if no speech within this


def _have(mod: str) -> bool:
    try:
        __import__(mod)
        return True
    except ImportError:
        return False


def _have_tts() -> bool:
    import shutil
    if shutil.which("piper") or shutil.which("espeak"):
        return True
    return _have("pyttsx3")


def detect_capabilities() -> dict:
    return {
        "openwakeword": _have("openwakeword"),
        "audio_in": _have("sounddevice"),
        "tts": _have_tts(),
    }


def _record_seconds(seconds: float, sample_rate: int = VOICE_SAMPLE_RATE) -> str:
    import sounddevice as sd
    from scipy.io import wavfile

    audio = sd.rec(
        int(seconds * sample_rate),
        samplerate=sample_rate, channels=1, dtype="int16",
    )
    sd.wait()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wavfile.write(tmp.name, sample_rate, audio)
        return tmp.name


def _transcribe(path: str) -> str:
    from voice.stt import transcribe_file
    try:
        return transcribe_file(path).strip()
    finally:
        Path(path).unlink(missing_ok=True)


def _speak(text: str, max_chars: int) -> None:
    from voice.tts import speak
    snippet = text.strip()
    if len(snippet) > max_chars:
        snippet = snippet[: max_chars - 1].rstrip() + "…"
    speak(snippet)


_STOP_RE = re.compile(
    r"\b(stop|wait|quiet|shut\s+up|hush|enough|cancel|abort)\b",
    re.IGNORECASE,
)


def _is_interrupt(text: str, wake_words: tuple[str, ...]) -> bool:
    """User said something that should kill ongoing TTS playback."""
    if _STOP_RE.search(text or ""):
        return True
    if _contains_wake(text, wake_words):
        return True
    return False


_PUNCT_RE = re.compile(r"[^\w\s]")


def _normalize(text: str) -> str:
    return _PUNCT_RE.sub(" ", (text or "").lower()).strip()


# Whisper sometimes hallucinates these on silence/ambient noise. Reject them
# before treating a transcript as a real command.
_WHISPER_NOISE = {
    "thanks for watching", "thank you", "thanks", "thank you for watching",
    "you", ".", "...", "bye", "goodbye", "music",
    "subscribe", "like and subscribe", "please subscribe",
    "see you next time", "see you", "bye bye",
    "okay", "ok", "uh", "um", "hmm", "mm",
}


def _looks_like_noise(text: str) -> bool:
    """Filter Whisper hallucinations and 1-word artifacts that shouldn't trigger commands."""
    norm = _normalize(text)
    if not norm:
        return True
    if norm in _WHISPER_NOISE:
        return True
    # Single short word with no semantic value
    if len(norm) <= 2:
        return True
    # Repeated character / token (e.g. "youyouyou", "okokok")
    if len(set(norm.split())) == 1 and len(norm.split()) > 2:
        return True
    return False


def _contains_wake(transcript: str, wake_words: tuple[str, ...]) -> str | None:
    """Return the matched wake word if heard, else None."""
    norm = _normalize(transcript)
    if not norm:
        return None
    for w in wake_words:
        if re.search(rf"\b{re.escape(w.lower())}\b", norm):
            return w
    return None


class VoiceLoop:
    """Wraps wake-detect → greet → capture → agent → speak around a turn callback."""

    def __init__(
        self,
        run_turn: Callable[[str], str],
        config: VoiceConfig | None = None,
        console: Console | None = None,
    ):
        self.run_turn = run_turn
        self.cfg = config or VoiceConfig()
        self.console = console or Console()
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def _print(self, msg: str) -> None:
        self.console.print(msg)

    # ── shared helpers ──
    def _greet(self) -> None:
        if self.cfg.speak_replies and _have_tts():
            try:
                _speak(self.cfg.greeting, self.cfg.speak_max_chars)
            except Exception:
                pass
        self._print(f"[bold magenta]Ultron:[/bold magenta] {self.cfg.greeting}")

    def _capture_one(self) -> str | None:
        try:
            self._print("[bold cyan]🎤 listening…[/bold cyan]")
            wav = _record_seconds(self.cfg.record_seconds)
        except Exception as e:
            self._print(f"[red]mic error: {e}[/red]")
            return None
        try:
            self._print("[dim]   transcribing…[/dim]")
            text = _transcribe(wav)
        except Exception as e:
            self._print(f"[red]stt error: {e}[/red]")
            return None
        if not text:
            self._print("[yellow]   (no speech detected)[/yellow]")
            return None
        return text

    def _handle(self, message: str, listener=None) -> None:
        self._print(f"[bold]you[/bold] » {message}")
        try:
            reply = self.run_turn(message)
        except Exception as e:
            reply = f"⚠ agent error: {e}"
            self._print(f"[red]{reply}[/red]")
        if not reply:
            return
        if self.cfg.speak_replies and _have_tts():
            try:
                self._speak_interruptible(reply, listener)
            except Exception as e:
                self._print(f"[red]tts error: {e}[/red]")

    def _speak_interruptible(self, reply: str, listener) -> None:
        """Speak the reply with the listener PAUSED to prevent self-feedback.

        Without pausing, the mic picks up our own TTS through the speakers,
        Whisper transcribes it, and we end up wake-firing on our own voice.
        Tradeoff: no real-time "stop" interruption — user must wait for TTS
        to finish.
        """
        from voice.tts import speak
        snippet = reply.strip()
        if len(snippet) > self.cfg.speak_max_chars:
            snippet = snippet[: self.cfg.speak_max_chars - 1].rstrip() + "…"

        if listener is not None and hasattr(listener, "pause"):
            listener.pause()
        try:
            speak(snippet)  # blocks until playback fully done
        finally:
            if listener is not None and hasattr(listener, "resume"):
                listener.resume()

    # ── mode 1: keyword (whisper-based, continuous) ──
    def run_keyword(self) -> None:
        """Continuously listen via VAD-segmented utterances; trigger on wake word.

        Always-on: a single InputStream feeds VAD which yields whole utterances.
        No gaps between recordings — the mic is live the entire time.
        """
        from voice.listener import ContinuousListener

        self._print(
            f"[green]✓ Ultron online[/green] · listening for "
            f"[cyan]'{', '.join(self.cfg.wake_words)}'[/cyan] · "
            f"[dim]Ctrl-C to exit[/dim]"
        )

        # Pre-warm whisper so the first wake isn't laggy.
        try:
            from voice.stt import _model
            _model()
        except Exception:
            pass

        try:
            with ContinuousListener() as L:
                self._wake_loop(L)
        except KeyboardInterrupt:
            self._print("\n[dim]bye[/dim]")
        except Exception as e:
            self._print(f"[red]listener crashed: {e}[/red]")

    def _wake_loop(self, L) -> None:
        """Drive the wake → command flow off a continuous utterance stream."""
        awaiting_command = False
        await_started_at = 0.0
        for wav in L.utterances():
            if self._stop.is_set():
                break
            try:
                text = _transcribe(wav)
            except Exception as e:
                self._print(f"[red]stt error: {e}[/red]")
                continue

            # Drop empty / hallucinated transcripts before they can become commands.
            if _looks_like_noise(text):
                continue

            # Stale awaiting_command? Drop it so ambient noise can't become a command.
            if awaiting_command and (time.time() - await_started_at) > self.cfg.command_timeout_sec:
                self._print("[dim]   (no command within timeout — back to wake)[/dim]")
                awaiting_command = False

            if not awaiting_command:
                matched = _contains_wake(text, self.cfg.wake_words)
                if not matched:
                    continue
                self._print(f"[bold green]🦾 wake heard:[/bold green] [dim]{text}[/dim]")
                tail = re.sub(
                    rf".*\b{re.escape(matched)}\b",
                    "", text, count=1, flags=re.IGNORECASE,
                ).strip(",. !?")
                if tail and not _looks_like_noise(tail):
                    self._handle(tail, listener=L)
                else:
                    self._greet()
                    awaiting_command = True
                    await_started_at = time.time()
                continue

            # We just greeted; this utterance is the actual command.
            awaiting_command = False
            self._handle(text, listener=L)

    # ── mode 2: openwakeword (built-in phrases only) ──
    def run_openwakeword(self) -> None:
        from openwakeword.model import Model
        import sounddevice as sd
        import numpy as np

        SAMPLE_RATE = 16000
        FRAME = 1280
        try:
            model = Model(wakeword_models=list(WAKE_WORDS))
        except Exception as e:
            self._print(f"[red]wake model load failed: {e}[/red]")
            return

        self._print(
            f"[green]✓ Ultron online[/green] (openwakeword: "
            f"[cyan]{', '.join(w.replace('_',' ') for w in WAKE_WORDS)}[/cyan]) · "
            f"[dim]Ctrl-C to exit[/dim]"
        )

        q: queue.Queue = queue.Queue()
        def cb(indata, frames, t, status):
            q.put(bytes(indata))

        with sd.RawInputStream(
            samplerate=SAMPLE_RATE, blocksize=FRAME,
            dtype="int16", channels=1, callback=cb,
        ):
            while not self._stop.is_set():
                try:
                    chunk = q.get(timeout=0.5)
                except queue.Empty:
                    continue
                audio = np.frombuffer(chunk, dtype=np.int16)
                scores = model.predict(audio)
                if any(v >= self.cfg.wake_threshold for v in scores.values()):
                    self._print("[bold green]🦾 wake detected[/bold green]")
                    self._greet()
                    cmd = self._capture_one()
                    if cmd:
                        self._handle(cmd)
                    while not q.empty():
                        try:
                            q.get_nowait()
                        except queue.Empty:
                            break

    # ── mode 3: push-to-talk ──
    def run_ptt(self) -> None:
        self._print(
            "[green]✓ Voice mode (push-to-talk)[/green] · "
            "[dim]press Enter to record, type 'q' to exit[/dim]"
        )
        while not self._stop.is_set():
            try:
                line = input("→ press Enter to talk › ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                self._print("[dim]bye[/dim]")
                return
            if line in ("q", "quit", "exit"):
                return
            self._greet()
            text = self._capture_one()
            if text:
                self._handle(text)

    # ── entrypoint ──
    def run(self, prefer: str = "auto") -> None:
        caps = detect_capabilities()
        if not caps["audio_in"]:
            self._print(
                "[red]sounddevice not installed.[/red] "
                "Run: [cyan].venv/bin/pip install sounddevice scipy[/cyan]"
            )
            return
        if not caps["tts"]:
            self._print(
                "[yellow]No TTS backend found — replies will be text-only.[/yellow]\n"
                "[dim]Install one: piper (best), or `apt install espeak`[/dim]"
            )
            self.cfg.speak_replies = False

        mode = prefer
        if mode == "auto":
            mode = "keyword"

        try:
            if mode == "keyword":
                self.run_keyword()
            elif mode == "wake":
                if caps["openwakeword"]:
                    self.run_openwakeword()
                else:
                    self._print(
                        "[yellow]openwakeword not installed — falling back to keyword mode.[/yellow]"
                    )
                    self.run_keyword()
            else:
                self.run_ptt()
        except KeyboardInterrupt:
            self._print("\n[dim]bye[/dim]")
