"""Choose the right transcription backend for this machine.

Priority: an explicit ``DICTATE_BACKEND`` override wins; otherwise prefer MLX on
Apple Silicon (fastest), then faster-whisper everywhere else. If the preferred
backend isn't importable we fall back rather than crash, so a misconfigured
install still dictates (just slower).
"""

from __future__ import annotations

from ..config import CONFIG
from . import faster_whisper as _fw
from . import mlx as _mlx
from .base import BaseTranscriber


def create_transcriber() -> BaseTranscriber:
    choice = (CONFIG.backend or "auto").lower()

    if choice == "mlx":
        return _mlx.MLXTranscriber()
    if choice in ("faster-whisper", "faster_whisper", "fw"):
        return _fw.FasterWhisperTranscriber()

    # auto
    if _mlx.available():
        return _mlx.MLXTranscriber()
    if _fw.available():
        return _fw.FasterWhisperTranscriber()

    # Nothing installed cleanly — surface the more portable one so the error
    # message points at the dependency the user most likely needs.
    return _fw.FasterWhisperTranscriber()
