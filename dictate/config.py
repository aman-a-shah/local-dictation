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
    # --- Transcription backend -------------------------------------------
    # "auto" prefers MLX on Apple Silicon and faster-whisper everywhere else.
    # Force one with DICTATE_BACKEND=mlx | faster-whisper.
    backend: str = field(default_factory=lambda: _env("BACKEND", "auto"))

    # --- Transcription model ---------------------------------------------
    # MLX (Apple Silicon): large-v3-turbo is the sweet spot — near large-v3
    # quality at a fraction of the compute. Try …/whisper-base for max speed.
    mlx_model: str = field(default_factory=lambda: _env("MLX_MODEL", "mlx-community/whisper-large-v3-turbo"))
    # faster-whisper (Windows / Intel / CUDA): "auto" picks small.en on CPU and
    # large-v3-turbo on CUDA. Override with any faster-whisper model name/path.
    fw_model: str = field(default_factory=lambda: _env("FW_MODEL", "auto"))
    fw_device: str = field(default_factory=lambda: _env("FW_DEVICE", "auto"))   # auto|cpu|cuda
    fw_compute_type: str = field(default_factory=lambda: _env("FW_COMPUTE", ""))  # "" = auto

    # Forcing a language skips Whisper's language-detection pass (faster). Set to
    # "" / "auto" to let the model detect it.
    language: str = field(default_factory=lambda: _env("LANGUAGE", "en"))

    # --- Push-to-talk key -------------------------------------------------
    # macOS uses the fn/globe key (handled natively). On Windows fn emits no OS
    # event, so we default to Left Ctrl (hold). Configurable via DICTATE_HOTKEY
    # using pynput key names: ctrl_l, ctrl_r, alt_r, f8, …
    hotkey: str = field(default_factory=lambda: _env("HOTKEY", "ctrl_l"))

    # --- History ----------------------------------------------------------
    # Local-only SQLite history of transcriptions that powers the dashboard.
    # Set DICTATE_HISTORY=0 to record nothing.
    save_history: bool = field(default_factory=lambda: _env_bool("HISTORY", True))

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

    @property
    def model(self) -> str:
        """Back-compat alias used by the macOS UI; the active model is the MLX one there."""
        return self.mlx_model


CONFIG = Config()
