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
        quietly delivers silence ("stubborn, waveform won't react"). So before
        each take we rebuild the stream whenever the default input changed or the
        previous stream is gone. Building a fresh 16 kHz mono input stream costs
        only a few ms, paid while the key is held — well below human reaction time.
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

        # Build/refresh and start the stream. If the device vanished out from
        # under us the start can raise — rebuild once from scratch and retry so a
        # single bad take can't wedge capture until the app is restarted.
        try:
            self._ensure_stream()
            if not self._stream.active:
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

        # Keep the stream object alive but inactive between takes (cheap restart).
        # A dead device can throw here; drop the stream so the next take rebuilds.
        if self._stream is not None:
            try:
                if self._stream.active:
                    self._stream.stop()
            except Exception as exc:
                print(f"[audio] stream stop failed ({exc}); will rebuild", flush=True)
                self._discard_stream()

        if not frames:
            return np.zeros(0, dtype=np.float32), duration
        audio = np.concatenate(frames).astype(np.float32, copy=False)
        return audio, duration

    def close(self) -> None:
        self._discard_stream()
