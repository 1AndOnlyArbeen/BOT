"""Continuous microphone listener with VAD-based segmentation.

Why this exists: the previous approach used `sd.rec(N) + sd.wait()` which
records fixed-size chunks back-to-back. Between two `rec` calls the mic is
NOT listening — anything spoken during the gap is lost. For an always-on
assistant we need:

  [mic] --InputStream callback--> [frame queue] --VAD worker--> [utterance wavs]

Energy-based VAD (frame RMS vs threshold) — simpler than webrtcvad, good
enough for room speech. State machine:

  silence → (K loud frames in a row) → speech
  speech  → (M quiet frames in a row) → silence (emit segment)

Each emitted segment is a tempfile wav; the consumer transcribes & deletes it.
"""
from __future__ import annotations

import queue
import tempfile
import threading
import time
from collections import deque
from pathlib import Path
from typing import Iterator

import numpy as np

from config import VOICE_SAMPLE_RATE


SAMPLE_RATE = VOICE_SAMPLE_RATE
FRAME_MS = 30                       # 30 ms frames @ 16 kHz = 480 samples
FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000
SILENCE_RMS = 350                   # below this counts as silence
SPEECH_RMS = 600                    # above this is definitely speech
START_SPEECH_FRAMES = 3             # ~90 ms of loud frames = speech start
END_SILENCE_FRAMES = 22             # ~660 ms of quiet frames = speech end
PREROLL_FRAMES = 8                  # keep 240 ms before detected start so we
                                    # don't clip the leading consonant
MAX_UTTERANCE_SEC = 20              # hard cap to avoid runaway
MIN_UTTERANCE_FRAMES = 8            # ~240 ms — anything shorter is noise


def _rms(frame: np.ndarray) -> float:
    if frame.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(frame.astype(np.float32) ** 2)))


class ContinuousListener:
    """Runs an InputStream in the background and yields complete VAD-trimmed utterances.

    Usage:
        with ContinuousListener() as L:
            for wav_path in L.utterances():
                text = transcribe(wav_path)
                ...
                Path(wav_path).unlink()
    """

    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        silence_rms: float = SILENCE_RMS,
        speech_rms: float = SPEECH_RMS,
        end_silence_frames: int = END_SILENCE_FRAMES,
        max_utterance_sec: int = MAX_UTTERANCE_SEC,
    ) -> None:
        self.sample_rate = sample_rate
        self.silence_rms = silence_rms
        self.speech_rms = speech_rms
        self.end_silence_frames = end_silence_frames
        self.max_utterance_samples = max_utterance_sec * sample_rate
        self._frames: queue.Queue[np.ndarray] = queue.Queue(maxsize=2048)
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._stream = None
        # State carried across calls to next_utterance_or_none() so polling
        # doesn't restart the VAD state machine each time.
        self._poll_state: dict | None = None

    def pause(self) -> None:
        """Drop all incoming frames until resume(). Use during TTS playback so
        the assistant doesn't transcribe its own speakers."""
        self._paused.set()
        # Drain anything already buffered.
        while True:
            try:
                self._frames.get_nowait()
            except queue.Empty:
                break
        # Reset VAD state so we don't carry partial captures across the pause.
        self._poll_state = None

    def resume(self) -> None:
        # Drain a fresh tail so we start clean.
        while True:
            try:
                self._frames.get_nowait()
            except queue.Empty:
                break
        self._poll_state = None
        self._paused.clear()

    def is_paused(self) -> bool:
        return self._paused.is_set()

    def __enter__(self) -> "ContinuousListener":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()

    def start(self) -> None:
        import sounddevice as sd

        def _cb(indata, frames, t, status):
            if self._paused.is_set():
                return  # discard frames while paused (e.g. during TTS playback)
            try:
                self._frames.put_nowait(np.frombuffer(bytes(indata), dtype=np.int16).copy())
            except queue.Full:
                # Drop oldest frame so we never block the audio thread.
                try:
                    self._frames.get_nowait()
                    self._frames.put_nowait(np.frombuffer(bytes(indata), dtype=np.int16).copy())
                except queue.Empty:
                    pass

        self._stream = sd.RawInputStream(
            samplerate=self.sample_rate, blocksize=FRAME_SAMPLES,
            dtype="int16", channels=1, callback=_cb,
        )
        self._stream.start()

    def stop(self) -> None:
        self._stop.set()
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def utterances(self) -> Iterator[str]:
        """Yield wav paths for each detected utterance until stop() is called."""
        from scipy.io import wavfile

        preroll: deque[np.ndarray] = deque(maxlen=PREROLL_FRAMES)
        in_speech = False
        loud_run = 0
        silent_run = 0
        captured: list[np.ndarray] = []

        while not self._stop.is_set():
            try:
                frame = self._frames.get(timeout=0.5)
            except queue.Empty:
                continue
            r = _rms(frame)

            if not in_speech:
                preroll.append(frame)
                if r >= self.speech_rms:
                    loud_run += 1
                else:
                    loud_run = 0
                if loud_run >= START_SPEECH_FRAMES:
                    in_speech = True
                    captured = list(preroll)  # include preroll so we don't clip onset
                    preroll.clear()
                    silent_run = 0
                    loud_run = 0
                continue

            captured.append(frame)
            if r < self.silence_rms:
                silent_run += 1
            else:
                silent_run = 0

            total_samples = sum(f.size for f in captured)
            if silent_run >= self.end_silence_frames or total_samples >= self.max_utterance_samples:
                if len(captured) >= MIN_UTTERANCE_FRAMES:
                    yield self._emit(captured, wavfile)
                in_speech = False
                captured = []
                silent_run = 0
                loud_run = 0

    def _emit(self, frames: list[np.ndarray], wavfile_mod) -> str:
        audio = np.concatenate(frames)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wavfile_mod.write(tmp.name, self.sample_rate, audio)
            return tmp.name

    def next_utterance_or_none(self, timeout: float = 0.3) -> str | None:
        """Non-blocking utterance pull. Returns a wav path if a complete
        utterance was detected within `timeout` seconds, else None.

        Carries VAD state across calls so it works as a cooperative poll.
        """
        from scipy.io import wavfile

        if self._poll_state is None:
            self._poll_state = {
                "preroll": deque(maxlen=PREROLL_FRAMES),
                "in_speech": False,
                "loud_run": 0,
                "silent_run": 0,
                "captured": [],
            }
        s = self._poll_state

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and not self._stop.is_set():
            remaining = max(0.0, deadline - time.monotonic())
            try:
                frame = self._frames.get(timeout=min(0.1, remaining or 0.01))
            except queue.Empty:
                continue
            r = _rms(frame)
            if not s["in_speech"]:
                s["preroll"].append(frame)
                s["loud_run"] = s["loud_run"] + 1 if r >= self.speech_rms else 0
                if s["loud_run"] >= START_SPEECH_FRAMES:
                    s["in_speech"] = True
                    s["captured"] = list(s["preroll"])
                    s["preroll"].clear()
                    s["silent_run"] = 0
                    s["loud_run"] = 0
                continue
            s["captured"].append(frame)
            s["silent_run"] = s["silent_run"] + 1 if r < self.silence_rms else 0
            total = sum(f.size for f in s["captured"])
            if s["silent_run"] >= self.end_silence_frames or total >= self.max_utterance_samples:
                if len(s["captured"]) >= MIN_UTTERANCE_FRAMES:
                    wav = self._emit(s["captured"], wavfile)
                    s["in_speech"] = False
                    s["captured"] = []
                    s["silent_run"] = 0
                    s["loud_run"] = 0
                    return wav
                s["in_speech"] = False
                s["captured"] = []
                s["silent_run"] = 0
                s["loud_run"] = 0
        return None
