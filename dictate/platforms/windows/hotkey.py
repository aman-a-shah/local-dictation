"""Global push-to-talk listener for Windows.

The macOS build uses the fn/globe key, but on Windows fn is handled in keyboard
firmware and emits no OS event, so we use a normal key (default Left Ctrl, set by
``DICTATE_HOTKEY``). The catch: Ctrl is also half of Ctrl+C / Ctrl+V / Ctrl+Z, so
a naive "record while Ctrl is down" would start a recording on every shortcut.

Guard: when the trigger goes down we start capturing, but if *any other key* is
pressed before it's released we treat the chord as a shortcut, cancel the capture,
and ignore the eventual release. A clean press-and-release with no other key in
between is a real push-to-talk.

Uses pynput's WH_KEYBOARD_LL listener (a dedicated background thread), so it never
blocks the UI.
"""

from __future__ import annotations

from typing import Callable, Optional

from ...config import CONFIG


def _resolve_key(name: str):
    """Map a config key name (e.g. 'ctrl_l', 'f8') to a pynput key object."""
    from pynput.keyboard import Key

    name = (name or "ctrl_l").strip().lower()
    if hasattr(Key, name):
        return getattr(Key, name)
    # Single character key like 'a' — return the literal so comparison works.
    return name


class WindowsHotkey:
    def __init__(
        self,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
        log: Optional[Callable[[str], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None,
    ) -> None:
        self._on_press = on_press
        self._on_release = on_release
        self._on_cancel = on_cancel or (lambda: None)
        self._log = log or (lambda _m: None)
        self._trigger = _resolve_key(CONFIG.hotkey)
        self._is_down = False
        self._aborted = False
        self._listener = None

    def _matches(self, key) -> bool:
        from pynput.keyboard import KeyCode

        if key == self._trigger:
            return True
        # Char keys arrive as KeyCode; compare their .char.
        if isinstance(self._trigger, str) and isinstance(key, KeyCode):
            return key.char == self._trigger
        return False

    def _on_key_press(self, key) -> None:
        if self._matches(key):
            if not self._is_down:
                self._is_down = True
                self._aborted = False
                self._safe(self._on_press, "on_press")
            return
        # A different key while the trigger is held => this is a shortcut chord.
        if self._is_down and not self._aborted:
            self._aborted = True
            self._safe(self._on_cancel, "on_cancel")

    def _on_key_release(self, key) -> None:
        if not self._matches(key) or not self._is_down:
            return
        self._is_down = False
        if self._aborted:
            self._aborted = False
            return  # was a shortcut; nothing to transcribe
        self._safe(self._on_release, "on_release")

    def _safe(self, fn: Callable[[], None], label: str) -> None:
        try:
            fn()
        except Exception as exc:  # never let a callback kill the listener
            print(f"[hotkey] {label} error: {exc}", flush=True)

    def start_background(self) -> None:
        from pynput import keyboard

        self._listener = keyboard.Listener(
            on_press=self._on_key_press, on_release=self._on_key_release
        )
        self._listener.daemon = True
        self._listener.start()
        self._log(f"[hotkey] listening for push-to-talk key: {CONFIG.hotkey}")

    def run(self) -> None:
        """Blocking variant for the CLI front-end."""
        from pynput import keyboard

        with keyboard.Listener(
            on_press=self._on_key_press, on_release=self._on_key_release
        ) as listener:
            self._listener = listener
            listener.join()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
