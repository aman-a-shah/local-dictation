"""Whisper transcription via Apple MLX (Metal-accelerated on Apple Silicon).

Two speed tricks matter most here:

1. **Warm the model once at startup.** The first MLX inference pays for weight
   loading and Metal kernel compilation. We do that during launch with a dummy
   clip so the first *real* dictation is already fast.
2. **Trim silence before inference.** Whisper cost scales with audio length, so
   we cheaply drop leading/trailing dead air before handing it to the model.
"""

from __future__ import annotations

import numpy as np

import mlx_whisper

from .config import CONFIG


def _trim_silence(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    """Drop leading/trailing near-silence using a short-window energy gate.

    Keeps a small pad around speech so we never clip word onsets/offsets.
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


class Transcriber:
    def __init__(self) -> None:
        self.model = CONFIG.model
        self.language = CONFIG.language or None

    def warmup(self) -> None:
        """Force model load + kernel compilation so the first take is fast."""
        silence = np.zeros(CONFIG.sample_rate, dtype=np.float32)
        try:
            self._run(silence)
        except Exception as exc:  # pragma: no cover - best effort
            print(f"[transcriber] warmup skipped: {exc}", flush=True)

    def _run(self, audio: np.ndarray) -> dict:
        return mlx_whisper.transcribe(
            audio,
            path_or_hf_repo=self.model,
            language=self.language,
            # Dictation clips are independent thoughts; don't let the model
            # condition on prior text (faster, and avoids repetition loops).
            condition_on_previous_text=False,
            # Temperature 0 = greedy/deterministic = fastest and most stable.
            temperature=0.0,
            fp16=True,
            verbose=None,
        )

    def transcribe(self, audio: np.ndarray) -> str:
        if audio.size == 0:
            return ""
        audio = _trim_silence(audio, CONFIG.sample_rate)
        if audio.size == 0:
            return ""
        result = self._run(audio)
        return _clean(result.get("text", ""))


_HALLUCINATIONS = {
    "thank you.",
    "thanks for watching!",
    "you",
    ".",
    "[blank_audio]",
    "(silence)",
}


def _clean(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    # Whisper emits stock phrases on pure silence; drop the well-known ones.
    if text.lower() in _HALLUCINATIONS:
        return ""
    return text
