"""Central configuration for the dictation engine.

Every tunable lives here so the rest of the code stays declarative. Values can be
overridden with environment variables (prefix ``DICTATE_``) so you can experiment
without editing code, e.g. ``DICTATE_MODEL=mlx-community/whisper-tiny dictate``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str) -> str:
    return os.environ.get(f"DICTATE_{name}", default)


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(f"DICTATE_{name}", default))
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(f"DICTATE_{name}", default))
    except (TypeError, ValueError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(f"DICTATE_{name}")
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Config:
    # --- Transcription model ---------------------------------------------
    # large-v3-turbo is the sweet spot on Apple Silicon: near large-v3 quality
    # at a fraction of the compute. Swap to whisper-tiny/base for max speed or
    # distil-large for a middle ground via the DICTATE_MODEL env var.
    model: str = field(default_factory=lambda: _env("MODEL", "mlx-community/whisper-large-v3-turbo"))

    # Forcing a language skips Whisper's language-detection pass (faster). Set to
    # "" / "auto" to let the model detect it.
    language: str = field(default_factory=lambda: _env("LANGUAGE", "en"))

    # --- Audio capture ----------------------------------------------------
    # 16 kHz mono is Whisper's native rate, so capturing there avoids a resample.
    sample_rate: int = 16_000
    channels: int = 1
    blocksize: int = 1_600  # 100 ms blocks -> snappy start/stop

    # Ignore taps shorter than this (accidental brushes of the key).
    min_record_seconds: float = field(default_factory=lambda: _env_float("MIN_SECONDS", 0.30))
    # Hard ceiling so a stuck key can't grow an unbounded buffer.
    max_record_seconds: float = field(default_factory=lambda: _env_float("MAX_SECONDS", 120.0))

    # --- Text injection ---------------------------------------------------
    # Paste via clipboard + Cmd-V is instant and Unicode-safe. Typing char by
    # char (DICTATE_INJECT=type) is slower but works where paste is blocked.
    inject_method: str = field(default_factory=lambda: _env("INJECT", "paste"))
    restore_clipboard: bool = field(default_factory=lambda: _env_bool("RESTORE_CLIPBOARD", True))
    # Trailing space after each insert reads more naturally for continuous dictation.
    append_space: bool = field(default_factory=lambda: _env_bool("APPEND_SPACE", True))

    # --- Feedback ---------------------------------------------------------
    sound_feedback: bool = field(default_factory=lambda: _env_bool("SOUND", True))

    # --- Post-processing (polish) ----------------------------------------
    # Fast, deterministic cleanup of the transcript (regex only — adds no
    # perceptible latency). Currently: turn spoken enumerations into lists.
    polish: bool = field(default_factory=lambda: _env_bool("POLISH", True))
    # "numbered" -> "1. milk" ; "bullet" -> "- milk"
    list_style: str = field(default_factory=lambda: _env("LIST_STYLE", "numbered"))
    # Minimum items before an enumeration is reformatted as a list.
    min_list_items: int = field(default_factory=lambda: _env_int("MIN_LIST_ITEMS", 2))

    def __post_init__(self) -> None:
        object.__setattr__(self, "language", "" if self.language.lower() in {"auto", ""} else self.language)


CONFIG = Config()
