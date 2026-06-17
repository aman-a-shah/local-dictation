"""Application wiring: fn key -> record -> transcribe -> inject at cursor.

The hotkey callbacks stay featherweight so the event-tap thread never stalls:
key-down just starts the mic, key-up grabs the buffer and hands transcription to
a background worker. A single-worker queue serializes transcription + injection
so rapid consecutive takes land in the right order.
"""

from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from .audio import Recorder
from .config import CONFIG
from .feedback import Feedback
from .hotkey import FnHotkey
from .injector import inject
from .transcriber import Transcriber


class DictationApp:
    def __init__(self) -> None:
        self.recorder = Recorder()
        self.transcriber = Transcriber()
        self.feedback = Feedback()
        # One worker = transcriptions run off the event-tap thread but stay ordered.
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="dictate-stt")
        self._hotkey = FnHotkey(self._on_press, self._on_release)

    # -- hotkey callbacks (run on the event-tap thread; keep them fast) ------
    def _on_press(self) -> None:
        self.recorder.start()
        self.feedback.listening()
        print("\r🎙️  listening…", end="", flush=True)

    def _on_release(self) -> None:
        audio, duration = self.recorder.stop()
        if duration < CONFIG.min_record_seconds or audio.size == 0:
            print("\r                         \r", end="", flush=True)
            return
        print(f"\r⏳ transcribing {duration:0.1f}s…", end="", flush=True)
        self._pool.submit(self._process, audio, duration)

    # -- worker thread -------------------------------------------------------
    def _process(self, audio: np.ndarray, duration: float) -> None:
        t0 = time.monotonic()
        try:
            text = self.transcriber.transcribe(audio)
        except Exception as exc:
            self.feedback.error()
            print(f"\r❌ transcription failed: {exc}", flush=True)
            return

        elapsed = time.monotonic() - t0
        if not text:
            self.feedback.error()
            print(f"\r🤷 (nothing recognized)   ", flush=True)
            return

        inject(text)
        self.feedback.done()
        speed = duration / elapsed if elapsed > 0 else 0.0
        print(f"\r✅ {elapsed:0.2f}s ({speed:0.1f}× realtime)  “{text}”", flush=True)

    # -- lifecycle -----------------------------------------------------------
    def run(self) -> None:
        print(f"Loading model: {CONFIG.model}", flush=True)
        t0 = time.monotonic()
        self.transcriber.warmup()
        print(f"Model ready in {time.monotonic() - t0:0.1f}s.\n", flush=True)
        print(
            "┌──────────────────────────────────────────────┐\n"
            "│  Hold  fn (🌐)  and speak. Release to insert.  │\n"
            "│  Press Ctrl-C in this window to quit.          │\n"
            "└──────────────────────────────────────────────┘\n",
            flush=True,
        )
        try:
            self._hotkey.run()
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        print("\nShutting down…")
        self._pool.shutdown(wait=True)
        self.recorder.close()


def main() -> int:
    app = DictationApp()
    try:
        app.run()
    except PermissionError as exc:
        print(f"\n⚠️  {exc}\n", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0
    return 0
