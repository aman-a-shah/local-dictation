"""The dictation engine, decoupled from any UI.

Holds the record -> transcribe -> inject pipeline and emits state changes through
a callback. Both the terminal front-end (`app.py`) and the menu-bar app
(`menu_app.py`) drive this same engine; they differ only in how they render the
states it emits.

States emitted via ``on_state(state, info)``:
    "ready"        model warmed, idle and waiting
    "listening"    fn held, mic capturing
    "transcribing" fn released, model running        info={"duration": s}
    "result"       text inserted                     info={"text", "elapsed", "duration"}
    "empty"        nothing recognized / tap too short
    "error"        transcription raised              info={"error": str}
    "idle"         returned to rest (follows result/empty/error)
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Optional

import numpy as np

from .audio import Recorder
from .backends import create_transcriber
from .config import CONFIG
from .platforms import Feedback, inject
from .polish import polish
from .paths import log_path

StateCallback = Callable[[str, Optional[dict]], None]

_LOG_PATH = str(log_path())


def _dlog(message: str) -> None:
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%H:%M:%S')}  [engine] {message}\n")
    except OSError:
        pass


class DictationEngine:
    def __init__(self, on_state: Optional[StateCallback] = None) -> None:
        self.recorder = Recorder()
        self.transcriber = create_transcriber()
        self.feedback = Feedback()
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="dictate-stt")
        self._on_state: StateCallback = on_state or (lambda state, info=None: None)

    def _emit(self, state: str, info: Optional[dict] = None) -> None:
        try:
            self._on_state(state, info)
        except Exception as exc:  # a UI bug must never break dictation
            print(f"[engine] state callback error: {exc}", flush=True)

    def warmup(self) -> float:
        t0 = time.monotonic()
        self.transcriber.warmup()
        elapsed = time.monotonic() - t0
        self._emit("ready")
        return elapsed

    # -- hotkey callbacks (run on the event-tap / main thread; keep fast) ----
    def on_press(self) -> None:
        self.recorder.start()
        self.feedback.listening()
        self._emit("listening")

    def on_release(self) -> None:
        audio, duration = self.recorder.stop()
        rms = float(np.sqrt(np.mean(audio**2))) if audio.size else 0.0
        peak = float(np.abs(audio).max()) if audio.size else 0.0
        _dlog(f"release: {audio.size} samples, {duration:0.2f}s, rms={rms:0.4f}, peak={peak:0.4f}")
        if duration < CONFIG.min_record_seconds or audio.size == 0:
            self._emit("empty")
            self._emit("idle")
            return
        if rms < 1e-4:
            _dlog("audio is silent — likely missing Microphone permission for this app")
        self._emit("transcribing", {"duration": duration})
        self._pool.submit(self._process, audio, duration)

    def cancel(self) -> None:
        """Abort an in-progress capture without transcribing.

        Used by the Windows hotkey when it detects a Ctrl-chord shortcut (e.g.
        Ctrl+C) rather than a genuine push-to-talk hold.
        """
        if self.recorder._recording:  # cheap best-effort; stop + discard
            self.recorder.stop()
        self._emit("idle")

    # -- worker thread -------------------------------------------------------
    def _process(self, audio: np.ndarray, duration: float) -> None:
        t0 = time.monotonic()
        try:
            text = self.transcriber.transcribe(audio)
        except Exception as exc:
            self.feedback.error()
            self._emit("error", {"error": str(exc)})
            self._emit("idle")
            return

        if not text:
            elapsed = time.monotonic() - t0
            _dlog(f"transcribed in {elapsed:0.2f}s -> {text!r}")
            self.feedback.error()
            self._emit("empty")
            self._emit("idle")
            return

        # Polish is pure regex (sub-millisecond); include it in the timed window
        # so the log reflects the true time-to-paste.
        text = polish(text)
        elapsed = time.monotonic() - t0
        _dlog(f"transcribed+polished in {elapsed:0.2f}s -> {text!r}")

        inject(text)
        self.feedback.done()
        self._record_history(text, duration, elapsed)
        self._emit("result", {"text": text, "elapsed": elapsed, "duration": duration})
        self._emit("idle")

    def _record_history(self, text: str, duration: float, elapsed: float) -> None:
        """Persist a successful transcription locally (best-effort, never raises)."""
        if not CONFIG.save_history:
            return
        try:
            from .store import get_store

            get_store().add(
                text,
                duration_s=duration,
                elapsed_s=elapsed,
                model=getattr(self.transcriber, "model_name", ""),
                lang=CONFIG.language or "auto",
            )
        except Exception as exc:  # history must never break dictation
            _dlog(f"history write failed: {exc}")

    def shutdown(self) -> None:
        self._pool.shutdown(wait=True)
        self.recorder.close()
