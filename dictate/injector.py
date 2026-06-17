"""Insert text at the system cursor, wherever focus is.

Default strategy is clipboard paste: stash the user's clipboard, write our text,
synthesize ⌘V, then restore the clipboard a beat later. Paste is instant and
fully Unicode-safe (emoji, accents, CJK) regardless of the focused app's input
handling. A character-by-character typing fallback exists for the rare app that
blocks programmatic paste.
"""

from __future__ import annotations

import threading
import time

import Quartz
from AppKit import NSPasteboard, NSPasteboardTypeString

from .config import CONFIG

_V_KEYCODE = 9  # kVK_ANSI_V
_CMD_FLAG = Quartz.kCGEventFlagMaskCommand


def _post_cmd_v() -> None:
    src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
    down = Quartz.CGEventCreateKeyboardEvent(src, _V_KEYCODE, True)
    Quartz.CGEventSetFlags(down, _CMD_FLAG)
    up = Quartz.CGEventCreateKeyboardEvent(src, _V_KEYCODE, False)
    Quartz.CGEventSetFlags(up, _CMD_FLAG)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, down)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, up)


def _paste(text: str) -> None:
    pb = NSPasteboard.generalPasteboard()
    previous = pb.stringForType_(NSPasteboardTypeString) if CONFIG.restore_clipboard else None

    pb.clearContents()
    pb.setString_forType_(text, NSPasteboardTypeString)
    # Tiny settle so the pasteboard write is visible to the target app.
    time.sleep(0.02)
    _post_cmd_v()

    if CONFIG.restore_clipboard:
        def _restore() -> None:
            time.sleep(0.25)  # let the paste consume our text first
            cur = pb.stringForType_(NSPasteboardTypeString)
            # Only restore if we still own the clipboard (don't clobber a copy
            # the user made in the meantime).
            if cur == text:
                pb.clearContents()
                if previous is not None:
                    pb.setString_forType_(previous, NSPasteboardTypeString)

        threading.Thread(target=_restore, daemon=True).start()


def _type(text: str) -> None:
    """Fallback: emit the text as synthetic Unicode key events."""
    src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
    for ch in text:
        ev = Quartz.CGEventCreateKeyboardEvent(src, 0, True)
        Quartz.CGEventKeyboardSetUnicodeString(ev, len(ch), ch)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
        up = Quartz.CGEventCreateKeyboardEvent(src, 0, False)
        Quartz.CGEventKeyboardSetUnicodeString(up, len(ch), ch)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, up)


def inject(text: str) -> None:
    if not text:
        return
    if CONFIG.append_space:
        text = text + " "
    if CONFIG.inject_method == "type":
        _type(text)
    else:
        _paste(text)
