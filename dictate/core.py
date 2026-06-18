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
from .config import CONFIG
from .feedback import Feedback
from .injector import inject
from .polish import polish
from .transcriber import Transcriber

StateCallback = Callable[[str, Optional[dict]], None]

_LOG_PATH = os.path.expanduser("~/Library/Logs/LocalDictation.log")


def _dlog(message: str) -> None:
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%H:%M:%S')}  [engine] {message}\n")
    except OSError:
        pass


class DictationEngine:
    def __init__(self, on_state: Optional[StateCallback] = None) -> None:
        self.recorder = Recorder()
        self.transcriber = Transcriber()
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
        self._emit("result", {"text": text, "elapsed": elapsed, "duration": duration})
        self._emit("idle")

    def shutdown(self) -> None:
        self._pool.shutdown(wait=True)
        self.recorder.close()
