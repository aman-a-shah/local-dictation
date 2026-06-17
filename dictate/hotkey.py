"""Global push-to-talk listener for the ``fn`` (🌐 globe) key.

macOS reports ``fn`` as a modifier, so it surfaces as a *flagsChanged* event
rather than a keyDown/keyUp pair. We tap that event stream in listen-only mode
(never consuming events, so normal ``fn`` shortcuts keep working) and watch for
the globe key's own keycode (63) toggling the secondary-fn flag on and off.

A CGEventTap requires Accessibility permission and a running CFRunLoop, which is
why ``run()`` blocks on the main thread — that's by design for event taps.
"""

from __future__ import annotations

from typing import Callable

import Quartz

FN_KEYCODE = 63  # kVK_Function (the globe / fn key)
_FN_MASK = Quartz.kCGEventFlagMaskSecondaryFn


class FnHotkey:
    def __init__(self, on_press: Callable[[], None], on_release: Callable[[], None]) -> None:
        self._on_press = on_press
        self._on_release = on_release
        self._is_down = False
        self._tap = None

    def _callback(self, proxy, type_, event, refcon):  # noqa: ANN001
        # The system disables a tap that runs too long or is force-disabled;
        # re-enable it so we keep receiving events.
        if type_ in (Quartz.kCGEventTapDisabledByTimeout, Quartz.kCGEventTapDisabledByUserInput):
            if self._tap is not None:
                Quartz.CGEventTapEnable(self._tap, True)
            return event

        keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
        if keycode != FN_KEYCODE:
            return event

        fn_down = bool(Quartz.CGEventGetFlags(event) & _FN_MASK)
        if fn_down and not self._is_down:
            self._is_down = True
            try:
                self._on_press()
            except Exception as exc:  # never let a callback kill the tap
                print(f"[hotkey] on_press error: {exc}", flush=True)
        elif not fn_down and self._is_down:
            self._is_down = False
            try:
                self._on_release()
            except Exception as exc:
                print(f"[hotkey] on_release error: {exc}", flush=True)
        return event

    def install(self) -> None:
        """Create the tap and add it to the current run loop (does not block).

        Use this when something else (e.g. NSApplication) already owns the run
        loop. Raises PermissionError if Accessibility permission is missing.
        """
        self._tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionListenOnly,
            Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged),
            self._callback,
            None,
        )
        if self._tap is None:
            raise PermissionError(
                "Could not create event tap. Grant Accessibility permission in "
                "System Settings -> Privacy & Security -> Accessibility."
            )

        source = Quartz.CFMachPortCreateRunLoopSource(None, self._tap, 0)
        Quartz.CFRunLoopAddSource(
            Quartz.CFRunLoopGetCurrent(), source, Quartz.kCFRunLoopCommonModes
        )
        Quartz.CGEventTapEnable(self._tap, True)

    def run(self) -> None:
        """Install the tap and block on its own run loop (terminal/CLI mode)."""
        self.install()
        Quartz.CFRunLoopRun()
