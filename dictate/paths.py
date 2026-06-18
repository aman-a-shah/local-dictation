"""Per-OS locations for app data, logs, and model cache.

Uses platformdirs when available (the packaged apps bundle it) and falls back to
sensible hand-rolled defaults so the engine still runs from a bare checkout.

- macOS  : ~/Library/Application Support/LocalDictation , ~/Library/Logs
- Windows: %APPDATA%\\LocalDictation , %LOCALAPPDATA%\\LocalDictation\\Logs
- Linux  : ~/.local/share/LocalDictation , ~/.local/state/LocalDictation/log
"""

from __future__ import annotations

import os
import platform
from pathlib import Path

APP_NAME = "LocalDictation"


def _fallback_data_dir() -> Path:
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    if system == "Windows":
        base = os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming")
        return Path(base) / APP_NAME
    base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    return Path(base) / APP_NAME


def _fallback_log_dir() -> Path:
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Logs" / APP_NAME
    if system == "Windows":
        base = os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
        return Path(base) / APP_NAME / "Logs"
    base = os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state")
    return Path(base) / APP_NAME / "log"


def data_dir() -> Path:
    try:
        import platformdirs

        p = Path(platformdirs.user_data_dir(APP_NAME, appauthor=False))
    except Exception:
        p = _fallback_data_dir()
    p.mkdir(parents=True, exist_ok=True)
    return p


def log_dir() -> Path:
    try:
        import platformdirs

        p = Path(platformdirs.user_log_dir(APP_NAME, appauthor=False))
    except Exception:
        p = _fallback_log_dir()
    p.mkdir(parents=True, exist_ok=True)
    return p


def models_dir() -> Path:
    p = data_dir() / "models"
    p.mkdir(parents=True, exist_ok=True)
    return p


def db_path() -> Path:
    return data_dir() / "history.db"


def settings_path() -> Path:
    return data_dir() / "settings.json"


def log_path() -> Path:
    """Primary engine log file.

    On macOS this stays at the historical ~/Library/Logs/LocalDictation.log path
    so existing docs/troubleshooting keep working; elsewhere it lives under the
    per-OS log dir.
    """
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Logs" / "LocalDictation.log"
    return log_dir() / "LocalDictation.log"
