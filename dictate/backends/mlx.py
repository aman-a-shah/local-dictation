"""Whisper transcription via Apple MLX (Metal-accelerated, Apple Silicon only).

Near large-v3 quality at a fraction of the compute, typically 10-20x faster than
real time on M-series. Only importable on Apple Silicon, so the factory guards
its use behind an availability check.
"""

from __future__ import annotations

import numpy as np

from ..config import CONFIG
from .base import BaseTranscriber


class MLXTranscriber(BaseTranscriber):
    backend = "mlx"

    def __init__(self) -> None:
        self.model_name = CONFIG.mlx_model

    def warmup(self) -> None:
        silence = np.zeros(CONFIG.sample_rate, dtype=np.float32)
        try:
            self._run(silence)
        except Exception as exc:  # pragma: no cover - best effort
            print(f"[mlx] warmup skipped: {exc}", flush=True)

    def _run(self, audio: np.ndarray) -> str:
        import mlx_whisper

        result = mlx_whisper.transcribe(
            audio,
            path_or_hf_repo=self.model_name,
            language=self.language,
            # Dictation clips are independent thoughts; don't condition on prior
            # text (faster, avoids repetition loops).
            condition_on_previous_text=False,
            temperature=0.0,  # greedy/deterministic = fastest + most stable
            fp16=True,
            verbose=None,
        )
        return result.get("text", "")


def available() -> bool:
    """True only on Apple Silicon with mlx-whisper importable."""
    import platform

    if platform.system() != "Darwin" or platform.machine() != "arm64":
        return False
    try:
        import mlx_whisper  # noqa: F401
    except Exception:
        return False
    return True
