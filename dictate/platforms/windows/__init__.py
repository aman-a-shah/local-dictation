"""Windows platform layer."""

from __future__ import annotations

from typing import Callable, Optional

from . import permissions
from .feedback import Feedback
from .hotkey import WindowsHotkey
from .inject import inject

__all__ = ["inject", "Feedback", "make_hotkey", "permissions"]


def make_hotkey(
    on_press: Callable[[], None],
    on_release: Callable[[], None],
    log: Optional[Callable[[str], None]] = None,
    on_cancel: Optional[Callable[[], None]] = None,
):
    """Return the push-to-talk listener (default Left Ctrl, configurable)."""
    return WindowsHotkey(on_press, on_release, log=log, on_cancel=on_cancel)
