"""Background menu-bar app — no terminal required.

Launches as a macOS *accessory* app: a single 🎙️ icon lives in the menu bar
(no Dock icon, no window). The fn key works system-wide exactly as in the CLI;
this just renders the engine's state as the menu-bar glyph and a status line, and
gives you a Quit item.

Runs on AppKit's NSApplication run loop. The fn event-tap source is installed on
that same main run loop, and engine state changes (which originate on worker
threads) are marshalled back to the main thread before touching any UI.
"""

from __future__ import annotations

import fcntl
import os
import tempfile
import threading
import time

import objc
from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSAlert,
    NSMenu,
    NSMenuItem,
    NSStatusBar,
    NSVariableStatusItemLength,
)
from Foundation import NSObject

from .config import CONFIG
from .core import DictationEngine
from .hotkey import FnHotkey

_LOG_PATH = os.path.expanduser("~/Library/Logs/LocalDictation.log")


def _log(message: str) -> None:
    """Append a line to the app log (the app has no console when launched via Finder)."""
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {message}\n")
    except OSError:
        pass


# Menu-bar glyph + status line for each engine state.
_GLYPH = {
    "loading": "⏳",
    "ready": "🎙️",
    "listening": "🔴",
    "transcribing": "✍️",
    "error": "⚠️",
    "blocked": "⚠️",
}


class DictationController(NSObject):
    def initWithEngine_(self, engine):  # noqa: N802 (ObjC selector form)
        self = objc.super(DictationController, self).init()
        if self is None:
            return None
        self.engine = engine
        self.statusItem = None
        self.stateItem = None
        self.lastItem = None
        self.hotkey = None
        self._pending = []  # (state, info) queued from worker threads
        self._pending_lock = threading.Lock()
        return self

    # -- UI construction (main thread) --------------------------------------
    @objc.python_method
    def build(self):
        bar = NSStatusBar.systemStatusBar()
        self.statusItem = bar.statusItemWithLength_(NSVariableStatusItemLength)
        self.statusItem.button().setTitle_(_GLYPH["loading"])

        menu = NSMenu.alloc().init()

        self.stateItem = self._item("Loading model…", None)
        menu.addItem_(self.stateItem)
        self.lastItem = self._item("Last: —", None)
        menu.addItem_(self.lastItem)
        menu.addItem_(NSMenuItem.separatorItem())

        hint = self._item(f"Model: {CONFIG.model.split('/')[-1]}", None)
        menu.addItem_(hint)
        menu.addItem_(NSMenuItem.separatorItem())

        quit_item = self._item("Quit Local Dictation", "quitApp:")
        quit_item.setKeyEquivalent_("q")
        menu.addItem_(quit_item)

        self.statusItem.setMenu_(menu)

    @objc.python_method
    def _item(self, title, action):
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action, "")
        if action is None:
            item.setEnabled_(False)
        else:
            item.setTarget_(self)
        return item

    # -- app delegate: fires once the app is fully launched & able to show UI -
    def applicationDidFinishLaunching_(self, _notification):  # noqa: N802
        try:
            self.build()
            self._ensure_mic()  # now the system can actually present the prompt
            # Use a module-level plain function as the thread target: invoking an
            # @objc.python_method from a fresh thread is unreliable under the
            # py2app/pyobjc runtime, but plain functions thread fine.
            threading.Thread(target=_do_warmup, args=(self,), daemon=True).start()
        except Exception:
            import traceback
            _log("FATAL in applicationDidFinishLaunching:\n" + traceback.format_exc())

    @objc.python_method
    def _ensure_mic(self):
        # PortAudio won't reliably prompt for mic access, so do it explicitly here
        # (otherwise the app silently records zeros -> "nothing recognized").
        from . import permissions

        status = permissions.mic_status()
        _log(f"microphone permission: {permissions.mic_status_name()}")
        if status == permissions.DENIED:
            # macOS won't prompt again once denied — user must flip it manually.
            self._show_state("blocked", "Enable Microphone in System Settings")
            self._alert(
                "Microphone access is off",
                "Local Dictation needs the microphone to hear you. Turn it on under "
                "System Settings → Privacy & Security → Microphone, then relaunch.",
            )
        elif status != permissions.AUTHORIZED:
            def done(granted):
                _log(f"microphone access granted: {bool(granted)}")

            permissions.request_mic(done)

    def installHotkey_(self, _):  # noqa: N802
        from . import permissions

        # Posting ⌘V to paste needs Accessibility — a *different* grant from the
        # one that lets us hear the fn key. If it's missing, the fn key still
        # triggers transcription but the paste is silently dropped.
        trusted = permissions.accessibility_trusted()
        _log(f"accessibility trusted (can paste): {trusted}")
        if not trusted:
            permissions.request_accessibility()  # opens the System Settings deep-link
            self._alert(
                "One more permission needed",
                "Local Dictation can hear the fn key but can't paste text yet. "
                "Add it under System Settings → Privacy & Security → Accessibility "
                "(toggle it ON), then quit and relaunch the app.",
            )

        self.hotkey = FnHotkey(self.engine.on_press, self.engine.on_release)
        try:
            self.hotkey.install()
            _log("fn hotkey installed — ready to dictate")
        except PermissionError as exc:
            _log(f"BLOCKED: {exc}")
            self._show_state("blocked", "Needs Accessibility permission")
            self._alert(
                "Accessibility permission needed",
                f"{exc}\n\nAdd “Local Dictation” under System Settings → Privacy & "
                "Security → Accessibility, then quit and relaunch the app.",
            )

    # -- engine state bridge (callable from any thread) ---------------------
    @objc.python_method
    def onEngineState(self, state, info):
        # Keep all data as native Python objects (no ObjC bridging of dicts);
        # just wake the main thread to drain the queue.
        with self._pending_lock:
            self._pending.append((state, dict(info) if info else {}))
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "drainStates:", None, False
        )

    def drainStates_(self, _):  # noqa: N802 (runs on main thread)
        while True:
            with self._pending_lock:
                if not self._pending:
                    return
                state, info = self._pending.pop(0)
            self._render_state(state, info)

    @objc.python_method
    def _render_state(self, state, info):
        g = info.get

        if state == "ready":
            self._show_state("ready", "Ready — hold fn (🌐) to dictate")
        elif state == "listening":
            self._show_state("listening", "Listening…")
        elif state == "transcribing":
            self._show_state("transcribing", f"Transcribing {float(g('duration', 0)):0.1f}s…")
        elif state == "result":
            text = str(g("text", ""))
            elapsed = float(g("elapsed", 0))
            self.lastItem.setTitle_(f"Last: “{_truncate(text)}”  ({elapsed:0.1f}s)")
            self._show_state("ready", "Inserted ✓")
        elif state == "empty":
            self._show_state("ready", "Nothing recognized")
        elif state == "error":
            self._show_state("error", f"Error: {_truncate(str(g('error', '')))}")
        elif state == "idle":
            self._glyph("ready")  # leave the status line on its last message

    @objc.python_method
    def _show_state(self, glyph_key, message):
        self._glyph(glyph_key)
        if self.stateItem is not None:
            self.stateItem.setTitle_(message)

    @objc.python_method
    def _glyph(self, glyph_key):
        if self.statusItem is not None:
            self.statusItem.button().setTitle_(_GLYPH.get(glyph_key, "🎙️"))

    @objc.python_method
    def _alert(self, title, message):
        alert = NSAlert.alloc().init()
        alert.setMessageText_(title)
        alert.setInformativeText_(message)
        alert.runModal()

    # -- menu actions -------------------------------------------------------
    def quitApp_(self, _):  # noqa: N802
        try:
            self.engine.shutdown()
        finally:
            NSApplication.sharedApplication().terminate_(self)


def _do_warmup(controller):
    """Warm the model off the main thread, then install the fn tap on the main run loop.

    A plain module-level function (not a controller method) so it threads reliably
    under py2app. ``controller.engine`` is a plain Python object; the only ObjC
    touch is performSelectorOnMainThread, which is designed to be called from
    background threads.
    """
    try:
        _log("warming up model…")
        elapsed = controller.engine.warmup()  # emits "ready" -> drainStates_ on main
        _log(f"model ready in {elapsed:0.1f}s")
        controller.performSelectorOnMainThread_withObject_waitUntilDone_(
            "installHotkey:", None, False
        )
    except Exception:
        import traceback
        _log("FATAL in warmup:\n" + traceback.format_exc())


def _truncate(text, limit=48):
    text = text.strip().replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 1] + "…"


# Held for the process lifetime so the OS keeps the lock; never closed explicitly.
_INSTANCE_LOCK = None


def _acquire_single_instance() -> bool:
    """Return True if we got the lock; False if another instance already holds it.

    Two instances would mean two event taps firing on every fn press -> doubled
    audio and doubled text insertion.
    """
    global _INSTANCE_LOCK
    path = os.path.join(tempfile.gettempdir(), "local-dictation.lock")
    _INSTANCE_LOCK = open(path, "w")
    try:
        fcntl.flock(_INSTANCE_LOCK, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def main() -> int:
    app = NSApplication.sharedApplication()
    # Accessory = menu-bar presence, no Dock icon, no window.
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    _log("=== Local Dictation launching ===")
    if not _acquire_single_instance():
        _log("another instance is already running — exiting")
        return 0

    engine = DictationEngine()
    controller = DictationController.alloc().initWithEngine_(engine)
    engine._on_state = controller.onEngineState  # wire engine -> UI

    # Defer all setup to applicationDidFinishLaunching: the app must be fully
    # launched before macOS will present the microphone-permission prompt.
    app.setDelegate_(controller)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
