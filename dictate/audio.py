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

    # -- Control ------------------------------------------------------------
    def start(self) -> None:
        with self._lock:
            if self._recording:
                return
            self._frames = []
            self._collected = 0
            self._recording = True
            self._start_time = time.monotonic()

        if self._stream is None:
            self._stream = sd.InputStream(
                samplerate=CONFIG.sample_rate,
                channels=CONFIG.channels,
                blocksize=CONFIG.blocksize,
                dtype="float32",
                callback=self._callback,
            )
        if not self._stream.active:
            self._stream.start()

    def stop(self) -> tuple[np.ndarray, float]:
        """Stop capture and return (audio float32 @16k, duration seconds)."""
        with self._lock:
            self._recording = False
            self._level = 0.0
            duration = time.monotonic() - self._start_time
            frames = self._frames
            self._frames = []

        # Keep the stream object alive but inactive between takes: re-starting an
        # existing stream is far cheaper than building a new one each press.
        if self._stream is not None and self._stream.active:
            self._stream.stop()

        if not frames:
            return np.zeros(0, dtype=np.float32), duration
        audio = np.concatenate(frames).astype(np.float32, copy=False)
        return audio, duration

    def close(self) -> None:
        if self._stream is not None:
            self._stream.close()
            self._stream = None
