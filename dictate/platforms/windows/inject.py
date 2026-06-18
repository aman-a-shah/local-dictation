"""Insert text at the system cursor on Windows.

Same strategy as macOS: stash the clipboard, write our text, synthesize Ctrl+V,
then restore the clipboard a beat later. Clipboard paste is instant and fully
Unicode-safe regardless of the focused app, which matters for accented/CJK/emoji
output. A character-by-character typing fallback covers apps that block paste.
"""

from __future__ import annotations

import threading
import time

from ...config import CONFIG


def _set_clipboard(text: str) -> None:
    import pyperclip

    pyperclip.copy(text)


def _get_clipboard() -> str:
    import pyperclip

    try:
        return pyperclip.paste()
    except Exception:
        return ""


def _press_ctrl_v() -> None:
    from pynput.keyboard import Controller, Key

    kb = Controller()
    with kb.pressed(Key.ctrl):
        kb.press("v")
        kb.release("v")


def _paste(text: str) -> None:
    previous = _get_clipboard() if CONFIG.restore_clipboard else None

    _set_clipboard(text)
    time.sleep(0.05)  # let the clipboard write settle before Ctrl+V
    _press_ctrl_v()

    if CONFIG.restore_clipboard:
        def _restore() -> None:
            time.sleep(0.5)  # let the paste consume our text first
            if _get_clipboard() == text:  # only if we still own the clipboard
                _set_clipboard(previous if previous is not None else "")

        threading.Thread(target=_restore, daemon=True).start()


def _type(text: str) -> None:
    """Fallback: emit the text as synthetic key presses (Unicode-capable)."""
    from pynput.keyboard import Controller

    Controller().type(text)


def inject(text: str) -> None:
    if not text:
        return
    if CONFIG.append_space:
        text = text + " "
    if CONFIG.inject_method == "type":
        _type(text)
    else:
        _paste(text)
