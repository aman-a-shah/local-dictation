"""Global push-to-talk listener for the ``fn`` (🌐 globe) key.

macOS reports ``fn`` as a modifier, so it surfaces as a *flagsChanged* event
rather than a keyDown/keyUp pair. We tap that event stream in listen-only mode
(never consuming events, so normal ``fn`` shortcuts keep working) and watch for
the globe key's own keycode (63) toggling the secondary-fn flag on and off.

A CGEventTap requires Accessibility permission and a running CFRunLoop, which is
why ``run()`` blocks on the main thread — that's by design for event taps.
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

import Quartz

FN_KEYCODE = 63  # kVK_Function (the globe / fn key)
_FN_MASK = Quartz.kCGEventFlagMaskSecondaryFn


class FnHotkey:
    def __init__(
        self,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
        log: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._on_press = on_press
        self._on_release = on_release
        self._is_down = False
        self._tap = None
        self._log = log or (lambda _m: None)
        self._thread: Optional[threading.Thread] = None

    def _callback(self, proxy, type_, event, refcon):  # noqa: ANN001
        # The system disables a tap that runs too long or is force-disabled;
        # re-enable it so we keep receiving events. Crucially, fn transitions
        # that arrive *while the tap is disabled are lost* — that drops a press
        # or release and chops an utterance into fragments. We log it so a
        # recurrence is diagnosable instead of a mystery.
        if type_ in (Quartz.kCGEventTapDisabledByTimeout, Quartz.kCGEventTapDisabledByUserInput):
            reason = "timeout" if type_ == Quartz.kCGEventTapDisabledByTimeout else "user-input"
            self._log(f"[hotkey] tap disabled ({reason}) — re-enabling (events may have been dropped)")
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

    def start_background(self) -> None:
        """Run the tap on its OWN thread + run loop, isolated from the UI.

        The menu-bar app's main run loop also drives the 60 fps waveform overlay;
        sharing it with the event tap lets heavy UI drawing starve the tap past
        its servicing deadline, so macOS disables it and drops fn transitions
        (an utterance gets chopped into empty fragments). A dedicated thread with
        its own CFRunLoop can never be starved by AppKit. The callbacks here are
        lightweight (recorder start/stop + queue a UI update) and already
        thread-safe, and UI updates marshal back to the main thread themselves.

        Raises PermissionError synchronously if the tap can't be created (so the
        caller can surface the Accessibility prompt) — the run loop only spins up
        once the tap exists.
        """
        ready = threading.Event()
        error: list[BaseException] = []

        def _run() -> None:
            try:
                self.install()  # adds the source to THIS thread's run loop
            except BaseException as exc:  # noqa: BLE001 — relay to the caller
                error.append(exc)
                ready.set()
                return
            self._log("[hotkey] tap running on dedicated thread")
            ready.set()
            Quartz.CFRunLoopRun()  # blocks this thread, not the UI

        self._thread = threading.Thread(target=_run, name="fn-hotkey", daemon=True)
        self._thread.start()
        ready.wait()
        if error:
            raise error[0]

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
