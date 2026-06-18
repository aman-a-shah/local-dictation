"""Pluggable transcription backends.

The engine talks to a single :class:`~dictate.backends.base.BaseTranscriber`
interface; which concrete backend backs it is chosen at runtime by
:func:`~dictate.backends.factory.create_transcriber` based on the platform and
what's installed:

- **MLX** (``mlx.py``) — Metal-accelerated, Apple-Silicon-only fast path.
- **faster-whisper** (``faster_whisper.py``) — CTranslate2, runs on Windows and
  Intel Macs (CPU) and on CUDA GPUs; also the universal fallback.
"""

from .base import BaseTranscriber
from .factory import create_transcriber

__all__ = ["BaseTranscriber", "create_transcriber"]
