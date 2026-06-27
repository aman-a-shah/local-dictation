"""Low-latency microphone capture.

The recorder keeps a single PortAudio input stream that we start and stop on
key-down / key-up. Frames arrive on PortAudio's callback thread and are appended
to a list (an O(1), allocation-light operation) so the callback never blocks —
critical for not dropping audio. On stop we concatenate once into a float32
array at Whisper's native 16 kHz, ready to hand straight to the model.
"""

from __future__ import annotations

import threading
import time
from typing import Optional

import numpy as np
import sounddevice as sd

from .config import CONFIG


class Recorder:
    def __init__(self) -> None:
        self._stream: Optional[sd.InputStream] = None
        self._stream_device = None   # identity of the device the stream was built for
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._start_time = 0.0
        self._recording = False
        self._max_frames = int(CONFIG.max_record_seconds * CONFIG.sample_rate)
        self._collected = 0
        # Live RMS of the most recent block, for the visual overlay to react to.
        # Written on the audio thread, read (best-effort) on the UI thread; a
        # float assignment is atomic in CPython, so no lock is needed for it.
        self._level = 0.0

    @property
    def level(self) -> float:
        """Loudness (RMS, ~0..0.3) of the latest captured block; 0 when idle."""
        return self._level

    # -- PortAudio callback (runs on a dedicated high-priority thread) ------
    def _callback(self, indata, frames, time_info, status) -> None:  # noqa: ANN001
        if status:
            # Overflows are non-fatal; just note them on stderr via print.
            print(f"[audio] {status}", flush=True)
        # The stream is left running *between* takes (kept warm so the next press
        # captures instantly), so blocks keep arriving while idle. Drop them with a
        # cheap unsynchronised flag read before doing any work — the authoritative
        # check happens again under the lock below.
        if not self._recording:
            return
        block = indata[:, 0]
        # Cheap loudness read for the overlay; fine to compute outside the lock.
        self._level = float(np.sqrt(np.mean(block * block))) if frames else 0.0
        with self._lock:
            if not self._recording:
                return
            if self._collected >= self._max_frames:
                return
            # Copy: PortAudio reuses the buffer after the callback returns.
            self._frames.append(block.copy())
            self._collected += frames

    # -- Stream lifecycle ---------------------------------------------------
    @staticmethod
    def _current_input_id():
        """A stable-ish identity for the current default input device.

        Returns (index, name) so we can tell when the OS default mic changed
        (AirPods connect, monitor unplugged, etc.). Best-effort: any failure
        returns None and we simply (re)build the stream.
        """
        try:
            info = sd.query_devices(kind="input")
            return (info.get("index"), info.get("name"))
        except Exception:
            return None

    def _discard_stream(self) -> None:
        """Tear down the current stream, swallowing errors from a dead device."""
        if self._stream is not None:
            try:
                self._stream.abort(ignore_errors=True)
            except Exception:
                pass
            try:
                self._stream.close(ignore_errors=True)
            except Exception:
                pass
        self._stream = None
        self._stream_device = None

    def _ensure_stream(self) -> None:
        """Guarantee a live stream bound to the *current* default input device.

        The original design kept one stream forever, but a PortAudio stream is
        pinned to the device it was opened on. Over days the user (un)plugs
        headphones / monitors / AirPods; the old stream then either errors or
        quietly delivers silence ("stubborn, waveform won't react"). So we
        rebuild the stream whenever the default input changed or the previous
        stream is gone.

        IMPORTANT: this calls ``sd.query_devices``, a synchronous CoreAudio
        query that can cost a couple hundred ms. Keep it OFF the key-press hot
        path — ``start`` must not call it for a warm stream. The device-change
        check runs instead at idle in ``pause`` (and once at startup in
        ``prewarm``), so a press only ever pays CoreAudio's stream start, never
        the device query.
        """
        current = self._current_input_id()
        if self._stream is not None and current != self._stream_device:
            self._discard_stream()
        if self._stream is None:
            self._stream = sd.InputStream(
                samplerate=CONFIG.sample_rate,
                channels=CONFIG.channels,
                blocksize=CONFIG.blocksize,
                dtype="float32",
                callback=self._callback,
            )
            self._stream_device = current

    def prewarm(self) -> None:
        """Open (but don't start) the input stream so the first ``start`` is cheap.

        Opening a CoreAudio stream negotiates the device and is the slow part of
        the first capture; doing it ahead of time keeps that cost off the first
        key-press. Best-effort: a failure here just means ``start`` builds it then.
        The stream is left inactive, so the mic-in-use indicator stays off.
        """
        with self._lock:
            self._ensure_stream()

    # -- Control ------------------------------------------------------------
    def start(self) -> None:
        with self._lock:
            if self._recording:
                return
            self._frames = []
            self._collected = 0
            self._recording = True
            self._start_time = time.monotonic()

        # Warm fast path: a stream left running between takes (see stop/pause)
        # captures the instant we flipped _recording on above. No device query,
        # no CoreAudio start — this is the common back-to-back case and must add
        # no perceptible latency between pressing fn and your voice landing.
        stream = self._stream
        if stream is not None and stream.active:
            return

        # Cold path: the idle window stopped the stream (or none exists yet).
        # Pay CoreAudio's ~180 ms start here, while the key is held before you
        # speak. We deliberately do NOT re-query the default device on this path
        # — that query is a large slice of the press-to-capture lag and runs off
        # the hot path in pause()/prewarm() instead, so by now the stream is
        # already bound to the right device. If the device vanished while idle,
        # start() raises and we rebuild once (which does query) and retry, so a
        # single bad take can't wedge capture until the app is restarted.
        try:
            if self._stream is None:
                self._ensure_stream()
            self._stream.start()
        except Exception as exc:
            print(f"[audio] stream start failed ({exc}); rebuilding", flush=True)
            self._discard_stream()
            try:
                self._ensure_stream()
                self._stream.start()
            except Exception as exc2:
                print(f"[audio] stream rebuild failed: {exc2}", flush=True)
                self._discard_stream()
                with self._lock:
                    self._recording = False

    def stop(self) -> tuple[np.ndarray, float]:
        """Stop capture and return (audio float32 @16k, duration seconds)."""
        # Measure the held duration at the moment of release (before the grace
        # wait) so the min-length filter judges the real hold, not hold+grace.
        duration = time.monotonic() - self._start_time

        # Grace window: keep the stream running a beat after release so the final
        # syllable — plus the block or two PortAudio still has buffered — lands in
        # our frames instead of being clipped. The callback keeps appending while
        # _recording stays True; we just wait, holding no lock.
        tail = CONFIG.tail_seconds
        if tail > 0 and self._recording:
            time.sleep(tail)

        with self._lock:
            self._recording = False
            self._level = 0.0
            frames = self._frames
            self._frames = []

        # Deliberately leave the stream RUNNING. A stopped CoreAudio input stream
        # takes ~180 ms to deliver its first sample on the next start — paid on
        # every press if we stop between takes. Keeping it warm makes a follow-up
        # press capture instantly (it just flips _recording back on). The engine
        # calls pause() to stop the stream after an idle window so the mic is
        # released and the "in use" dot turns off when you're done dictating.

        if not frames:
            return np.zeros(0, dtype=np.float32), duration
        audio = np.concatenate(frames).astype(np.float32, copy=False)
        return audio, duration

    def pause(self) -> None:
        """Stop the warm stream's IO to release the mic (turns off the in-use dot).

        Keeps the stream object open so the next start only rebuilds if the default
        device changed meanwhile. Never pauses mid-take. Best-effort: a dead device
        is discarded so the next start builds a fresh one.

        This is also where the (potentially slow) default-device check is paid:
        we're already idle and off the key-press path, so re-binding the stopped
        stream to the current default mic here means the next press's ``start``
        only pays CoreAudio's stream start, never the device query.
        """
        with self._lock:
            if self._recording:
                return
        if self._stream is None:
            return
        try:
            if self._stream.active:
                self._stream.stop()
        except Exception as exc:
            print(f"[audio] stream pause failed ({exc}); will rebuild", flush=True)
            self._discard_stream()
            return
        # Mic is released; now (off the hot path) re-bind to the current default
        # input if it changed while we were warm, so the next cold start is just
        # a stream.start(). A no-op when the device is unchanged.
        try:
            self._ensure_stream()
        except Exception as exc:
            print(f"[audio] device refresh on pause failed ({exc}); will rebuild", flush=True)
            self._discard_stream()

    def close(self) -> None:
        self._discard_stream()
