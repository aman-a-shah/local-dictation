"""Global push-to-talk listener for the ``fn`` (🌐 globe) key.

macOS reports ``fn`` as a modifier, so it surfaces as a *flagsChanged* event
rather than a keyDown/keyUp pair. We tap that event stream in listen-only mode
(never consuming events, so normal ``fn`` shortcuts keep working) and watch for
the globe key's own keycode (63) toggling the secondary-fn flag on and off.

A CGEventTap requires Accessibility permission and a running CFRunLoop, which is
why ``run()`` blocks on the main thread — that's by design for event taps.

Long-running robustness: a CGEventTap can be silently disabled by the system
(notably across sleep/wake or display reconfiguration) *without* always
delivering a disable event, and a single dropped ``fn`` transition would
otherwise wedge the press/release state forever ("works for a while, then stops
until I restart it"). A watchdog thread therefore polls the tap and re-enables /
resynchronises it, and a stuck hold is force-finalised. See ``_watchdog``.
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Optional

import Quartz

FN_KEYCODE = 63  # kVK_Function (the globe / fn key)
_FN_MASK = Quartz.kCGEventFlagMaskSecondaryFn

_WATCHDOG_INTERVAL = 1.5  # seconds between tap-health checks


class FnHotkey:
    def __init__(
        self,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
        log: Optional[Callable[[str], None]] = None,
        max_hold_seconds: float = 120.0,
    ) -> None:
        self._on_press = on_press
        self._on_release = on_release
        self._is_down = False
        self._down_since = 0.0
        self._max_hold = max_hold_seconds
        self._tap = None
        self._log = log or (lambda _m: None)
        self._thread: Optional[threading.Thread] = None
        self._watchdog_thread: Optional[threading.Thread] = None
        self._stop_watchdog = threading.Event()
        # Serialises press/release dispatch so the watchdog and the tap callback
        # can't both fire on_press/on_release at the same instant.
        self._dispatch_lock = threading.Lock()

    # -- press / release dispatch (serialised) ------------------------------
    def _fire_press(self) -> None:
        with self._dispatch_lock:
            if self._is_down:
                return
            self._is_down = True
            self._down_since = time.monotonic()
        try:
            self._on_press()
        except Exception as exc:  # never let a callback kill the tap
            print(f"[hotkey] on_press error: {exc}", flush=True)

    def _fire_release(self) -> None:
        with self._dispatch_lock:
            if not self._is_down:
                return
            self._is_down = False
        try:
            self._on_release()
        except Exception as exc:
            print(f"[hotkey] on_release error: {exc}", flush=True)

    @staticmethod
    def _fn_physically_down() -> bool:
        """Read the live secondary-fn flag straight from the HID layer.

        Lets the watchdog tell whether a press/release was missed (e.g. the
        transition arrived while the tap was disabled) and recover the state.
        """
        flags = Quartz.CGEventSourceFlagsState(
            Quartz.kCGEventSourceStateCombinedSessionState
        )
        return bool(flags & _FN_MASK)

    def _resync(self) -> None:
        """Make logical state match the keyboard's actual fn state.

        Called after we re-enable a tap that had been disabled: any transition
        during the dead window was dropped, so trust the hardware, not our cache.
        """
        physically_down = self._fn_physically_down()
        if physically_down and not self._is_down:
            self._fire_press()
        elif not physically_down and self._is_down:
            self._fire_release()

    def _callback(self, proxy, type_, event, refcon):  # noqa: ANN001
        # The system disables a tap that runs too long or is force-disabled;
        # re-enable it so we keep receiving events. Crucially, fn transitions
        # that arrive *while the tap is disabled are lost* — that drops a press
        # or release and chops an utterance into fragments. We log it so a
        # recurrence is diagnosable, then resync against the hardware so a
        # dropped release can't leave us stuck "holding".
        if type_ in (Quartz.kCGEventTapDisabledByTimeout, Quartz.kCGEventTapDisabledByUserInput):
            reason = "timeout" if type_ == Quartz.kCGEventTapDisabledByTimeout else "user-input"
            self._log(f"[hotkey] tap disabled ({reason}) — re-enabling (events may have been dropped)")
            if self._tap is not None:
                Quartz.CGEventTapEnable(self._tap, True)
            self._resync()
            return event

        keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
        if keycode != FN_KEYCODE:
            return event

        fn_down = bool(Quartz.CGEventGetFlags(event) & _FN_MASK)
        if fn_down:
            self._fire_press()
        else:
            self._fire_release()
        return event

    # -- watchdog -----------------------------------------------------------
    def _watchdog(self) -> None:
        """Keep the tap alive and the state unstuck for the life of the app.

        Polls because the disable *event* is not guaranteed across every sleep /
        wake or display change — but ``CGEventTapIsEnabled`` always tells the
        truth. Also force-finalises a hold that has run past the sane maximum
        (a genuinely stuck key or a release we never saw), which would otherwise
        leave the recorder running and ignore all further presses.
        """
        while not self._stop_watchdog.wait(_WATCHDOG_INTERVAL):
            try:
                tap = self._tap
                if tap is not None and not Quartz.CGEventTapIsEnabled(tap):
                    self._log("[hotkey] watchdog: tap was disabled — re-enabling")
                    Quartz.CGEventTapEnable(tap, True)
                    self._resync()
                if self._is_down and (time.monotonic() - self._down_since) > self._max_hold:
                    self._log("[hotkey] watchdog: hold exceeded max — force-finalising")
                    self._resync()
                    # If the key really is still down, _resync left it down; only
                    # force a release when the hardware agrees it's up.
                    if self._is_down and not self._fn_physically_down():
                        self._fire_release()
            except Exception as exc:  # the watchdog must never die
                print(f"[hotkey] watchdog error: {exc}", flush=True)

    def reenable(self) -> None:
        """Re-enable + resync the tap immediately (e.g. on system wake)."""
        if self._tap is not None:
            try:
                Quartz.CGEventTapEnable(self._tap, True)
                self._resync()
                self._log("[hotkey] tap re-enabled on demand")
            except Exception as exc:
                print(f"[hotkey] reenable error: {exc}", flush=True)

    # -- lifecycle ----------------------------------------------------------
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
        once the tap exists. A watchdog thread is started alongside to keep the
        tap alive across sleep/wake for the life of the process.
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

        self._watchdog_thread = threading.Thread(
            target=self._watchdog, name="fn-hotkey-watchdog", daemon=True
        )
        self._watchdog_thread.start()

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
