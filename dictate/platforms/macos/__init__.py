"""macOS platform layer — thin re-exports of the existing native modules.

The original pyobjc/Quartz implementations (``injector``, ``feedback``,
``hotkey``, ``permissions``) live at the top of the ``dictate`` package and are
battle-tested; this subpackage simply adapts them to the common platform
interface that :mod:`dictate.platforms` expects.
"""

from __future__ import annotations

from typing import Callable, Optional

from ...feedback import Feedback
from ...hotkey import FnHotkey
from ...injector import inject
from ... import permissions

__all__ = ["inject", "Feedback", "make_hotkey", "permissions"]


def make_hotkey(
    on_press: Callable[[], None],
    on_release: Callable[[], None],
    log: Optional[Callable[[str], None]] = None,
    on_cancel: Optional[Callable[[], None]] = None,
):
    """Return the fn-key push-to-talk listener (see FnHotkey).

    ``on_cancel`` is accepted for interface parity with the Windows hotkey (which
    cancels a capture when a Ctrl-chord shortcut is detected) but is unused on
    macOS, where the fn modifier never doubles as a shortcut.
    """
    return FnHotkey(on_press, on_release, log=log)
