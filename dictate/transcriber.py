"""Backwards-compatible shim.

The transcription logic moved into the pluggable :mod:`dictate.backends` package
so the same engine can run MLX on Apple Silicon and faster-whisper on Windows /
Intel. This module preserves the old import surface
(``from dictate.transcriber import Transcriber, _trim_silence``) used by tests and
older callers: ``Transcriber`` now resolves to whatever backend is right for this
machine.
"""

from __future__ import annotations

from .backends.base import _clean, _trim_silence, clean, trim_silence  # noqa: F401
from .backends.factory import create_transcriber


def Transcriber():  # noqa: N802 - kept callable like the old class constructor
    """Return the platform-appropriate transcriber (was a class; now a factory)."""
    return create_transcriber()


__all__ = ["Transcriber", "trim_silence", "_trim_silence", "clean", "_clean"]
