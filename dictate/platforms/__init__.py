"""Per-OS platform layer: text injection, audio cues, hotkey, permissions, tray.

The engine (:mod:`dictate.core`) and the app front-ends import everything they
need from here; this module forwards to the right OS implementation so no caller
ever imports a platform-specific module directly. That keeps Windows builds from
ever touching pyobjc and macOS builds from ever touching pywin32.
"""

from __future__ import annotations

import platform as _platform

_SYSTEM = _platform.system()

if _SYSTEM == "Windows":
    from .windows import Feedback, inject, make_hotkey, permissions
elif _SYSTEM == "Darwin":
    from .macos import Feedback, inject, make_hotkey, permissions
else:  # Linux / other — best-effort cross-platform pieces.
    from .windows import Feedback, inject, make_hotkey, permissions  # type: ignore

__all__ = ["inject", "Feedback", "make_hotkey", "permissions", "SYSTEM"]
SYSTEM = _SYSTEM


def hotkey_label() -> str:
    """Human-readable name of the push-to-talk key for this platform/config."""
    if _SYSTEM == "Darwin":
        return "fn (🌐)"
    from ..config import CONFIG

    pretty = {
        "ctrl_l": "Left Ctrl",
        "ctrl_r": "Right Ctrl",
        "alt_l": "Left Alt",
        "alt_r": "Right Alt",
        "cmd": "Win",
    }
    return pretty.get(CONFIG.hotkey, CONFIG.hotkey)
