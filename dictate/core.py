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
from .backends.base import has_speech
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
        # A *separate* single worker that owns BOTH ends of capture — starting the
        # mic on press and finalising it on release. It must not share the
        # transcription pool: if a previous clip is still transcribing, the next
        # release's capture has to stop *now*, not wait in line behind it. And it
        # must not run on the event-tap thread: opening/rebuilding the CoreAudio
        # input stream can take tens-to-hundreds of ms (cold device, or after the
        # default mic changes), which is long enough for macOS to blow the tap's
        # servicing deadline and *disable the whole tap* — dropping that press and
        # every event after it ("it just stops working after a while"). Press and
        # release both queue here, so start always runs before its matching stop.
        self._capture_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="dictate-cap")
        # Text injection (clipboard write + ⌘V to the window server) runs here, OFF
        # the transcription pool. A paste can block on a wedged window server; if it
        # shared the STT worker, that one stuck paste would queue every future
        # transcription behind it forever ("stopped working"). On its own worker a
        # stuck paste only delays later pastes, never transcription, and the overlay
        # still retracts. Single worker keeps pastes (and the clipboard) ordered.
        self._inject_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="dictate-inj")
        self._on_state: StateCallback = on_state or (lambda state, info=None: None)
        # When did the model last do real work? Used to decide whether to re-warm
        # it on the next key-down (see on_press). Starts "now" so the warmup at
        # launch counts and we don't double-warm the very first take.
        self._last_activity = time.monotonic()

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

    def prewarm_audio(self) -> None:
        """Open the mic stream ahead of the first press (best-effort, never raises).

        The cold CoreAudio device-open otherwise lands on the very first key-down.
        Building it now — before the hotkey is even installed, so no press can race
        it — means the first ``recorder.start()`` is just a cheap resume. Capture is
        not started, so the mic-in-use indicator stays off until you actually hold fn.
        """
        try:
            self.recorder.prewarm()
        except Exception as exc:  # best-effort; start() will rebuild on demand
            _dlog(f"audio prewarm skipped: {exc}")

    # -- hotkey callbacks (run on the event-tap thread; MUST return fast) -----
    # macOS disables an event tap whose callback overruns the servicing
    # deadline, dropping fn transitions. So these do the bare minimum and hand
    # any blocking work (the grace-window wait, transcription) to worker threads.
    def on_press(self) -> None:
        # Runs on the event-tap thread — it MUST return almost instantly or macOS
        # disables the tap (see _capture_pool). Emitting the UI state and the start
        # cue are non-blocking, so they stay here for instant feedback; the only
        # potentially-slow part — opening/resuming the mic stream — is handed to the
        # capture worker. The tiny hand-off latency is far below human reaction time
        # and never risks the tap.
        self._emit("listening")
        self.feedback.listening()
        self._capture_pool.submit(self._begin)

    def _begin(self) -> None:
        """Start capture off the tap thread (paired with _finalize on release)."""
        try:
            self._begin_impl()
        except Exception as exc:  # a worker task must never die or the pool wedges
            _dlog(f"begin failed: {exc}")

    def _begin_impl(self) -> None:
        self.recorder.start()
        # If the model has been idle long enough that the OS may have paged it
        # out, page it back in *now* — concurrently with you speaking — so the
        # real transcription on release runs hot. Queued on the transcription
        # pool so it serialises ahead of (and is usually finished before) the
        # real take. This is the main lever for "slow after a pause".
        idle = CONFIG.warm_after_idle
        if idle > 0 and (time.monotonic() - self._last_activity) > idle:
            self._pool.submit(self._prime)
        self._last_activity = time.monotonic()

    def _prime(self) -> None:
        """Cheap dummy inference to keep the model/Metal/pages warm. Never raises."""
        try:
            self.transcriber.warmup()
        except Exception as exc:  # priming is best-effort
            _dlog(f"prime skipped: {exc}")

    def on_release(self) -> None:
        # Don't touch the recorder here — recorder.stop() sleeps for the trailing
        # grace window, which must never run on the tap thread. Hand it off (to the
        # same worker as _begin, so stop always follows its matching start).
        self._capture_pool.submit(self._finalize)

    def _finalize(self) -> None:
        try:
            audio, duration = self.recorder.stop()  # includes the post-release grace
            rms = float(np.sqrt(np.mean(audio**2))) if audio.size else 0.0
            peak = float(np.abs(audio).max()) if audio.size else 0.0
            _dlog(f"release: {audio.size} samples, {duration:0.2f}s, rms={rms:0.4f}, peak={peak:0.4f}")
            if duration < CONFIG.min_record_seconds or audio.size == 0:
                self._emit("empty")
                self._emit("idle")
                return
            # Held the key but said nothing: skip the model entirely. Running
            # Whisper on a silent clip costs 1.5-5 s (it amplifies the room tone
            # and hallucinates a stock phrase we then discard) — and on an idle
            # model the real decode also waits behind the warm-up prime. The gate
            # keys off the clip's own dynamic range, so a genuine quiet word still
            # passes through; only clear silence is short-circuited.
            if not has_speech(audio, CONFIG.sample_rate):
                _dlog(f"no speech (silent clip, rms={rms:0.4f}) — skipping transcription")
                self.feedback.error()
                self._emit("empty")
                self._emit("idle")
                return
            if rms < 1e-4:
                _dlog("audio is silent — likely missing Microphone permission for this app")
            self._emit("transcribing", {"duration": duration})
            self._pool.submit(self._process, audio, duration)
        except Exception as exc:  # never let the capture worker die, never get stuck
            _dlog(f"finalize failed: {exc}")
            self._emit("idle")

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
        # The whole body is guarded and "idle" is emitted in `finally`, so no
        # matter what fails the worker survives and the overlay always retracts
        # (never left stuck in the "thinking" shimmer with its 60 fps timer running).
        t0 = time.monotonic()
        try:
            try:
                text = self.transcriber.transcribe(audio)
            except Exception as exc:
                self.feedback.error()
                self._emit("error", {"error": str(exc)})
                return

            if not text:
                elapsed = time.monotonic() - t0
                _dlog(f"transcribed in {elapsed:0.2f}s -> {text!r}")
                self.feedback.error()
                self._emit("empty")
                return

            # Polish is pure regex (sub-millisecond); include it in the timed window
            # so the log reflects the true time-to-paste.
            text = polish(text)
            elapsed = time.monotonic() - t0
            _dlog(f"transcribed+polished in {elapsed:0.2f}s -> {text!r}")

            self._emit("result", {"text": text, "elapsed": elapsed, "duration": duration})
            self._last_activity = time.monotonic()  # keep the warm window open
            # Deliver the text off this (STT) worker so a wedged paste can't stall
            # the next transcription; persistence is best-effort tail work.
            self._inject_pool.submit(self._deliver, text)
            self._record_history(text, duration, elapsed)
        except Exception as exc:  # defensive: keep the STT worker alive
            _dlog(f"process failed: {exc}")
            self._emit("error", {"error": str(exc)})
        finally:
            self._emit("idle")

    def _deliver(self, text: str) -> None:
        """Paste the text + play the done cue. Runs on the inject worker; guarded
        so a paste failure never kills the worker or leaks an exception."""
        try:
            inject(text)
            self.feedback.done()
        except Exception as exc:
            _dlog(f"inject failed: {exc}")

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
        self._capture_pool.shutdown(wait=False)
        self._inject_pool.shutdown(wait=False)
        self._pool.shutdown(wait=True)
        self.recorder.close()
