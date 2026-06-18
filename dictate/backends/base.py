"""Shared transcription primitives + the backend interface.

Silence trimming and hallucination cleanup are model-agnostic, so they live here
and are reused by every backend. A concrete backend only has to implement
``_run`` (raw audio -> text) and ``warmup``.
"""

from __future__ import annotations

import abc

import numpy as np

from ..config import CONFIG


def trim_silence(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    """Drop leading/trailing near-silence using a short-window energy gate.

    Keeps a small pad around speech so we never clip word onsets/offsets. This is
    the single biggest latency lever — Whisper cost scales with audio length.
    """
    if audio.size == 0:
        return audio

    win = max(1, sample_rate // 50)  # 20 ms windows
    n_windows = audio.size // win
    if n_windows < 3:
        return audio

    trimmed = audio[: n_windows * win].reshape(n_windows, win)
    rms = np.sqrt(np.mean(trimmed**2, axis=1) + 1e-9)
    # Adaptive threshold: a fraction of the loudest window, floored for quiet mics.
    threshold = max(rms.max() * 0.06, 0.0025)
    voiced = np.where(rms > threshold)[0]
    if voiced.size == 0:
        return audio  # all quiet -> let Whisper decide (likely empty)

    pad = 4  # ~80 ms of context on each side
    start = max(0, voiced[0] - pad) * win
    end = min(n_windows, voiced[-1] + 1 + pad) * win
    return audio[start:end]


# Backwards-compatible alias (the original lived in transcriber.py as _trim_silence).
_trim_silence = trim_silence


_HALLUCINATIONS = {
    "thank you.",
    "thanks for watching!",
    "you",
    ".",
    "[blank_audio]",
    "(silence)",
}


def clean(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    # Whisper emits stock phrases on pure silence; drop the well-known ones.
    if text.lower() in _HALLUCINATIONS:
        return ""
    return text


_clean = clean


class BaseTranscriber(abc.ABC):
    """Common scaffolding: trim -> run -> clean. Subclasses implement ``_run``."""

    #: Human-readable name of the loaded model (for UI/status lines).
    model_name: str = ""
    #: Short backend id ("mlx" / "faster-whisper") for diagnostics + the dashboard.
    backend: str = "base"

    @property
    def language(self) -> str | None:
        return CONFIG.language or None

    @abc.abstractmethod
    def warmup(self) -> None:
        """Force model load + kernel compilation so the first real take is fast."""

    @abc.abstractmethod
    def _run(self, audio: np.ndarray) -> str:
        """Transcribe already-trimmed audio to raw (uncleaned) text."""

    def transcribe(self, audio: np.ndarray) -> str:
        if audio.size == 0:
            return ""
        audio = trim_silence(audio, CONFIG.sample_rate)
        if audio.size == 0:
            return ""
        return clean(self._run(audio))
