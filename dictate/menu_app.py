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
    NSBezierPath,
    NSColor,
    NSFontWeightRegular,
    NSImage,
    NSImageSymbolConfiguration,
    NSMenu,
    NSMenuItem,
    NSStatusBar,
    NSVariableStatusItemLength,
    NSWorkspace,
)
from Foundation import NSMakeRect, NSMakeSize, NSObject, NSRunLoopCommonModes

from .config import CONFIG
from .core import DictationEngine
from .hotkey import FnHotkey
from .overlay import Overlay

_LOG_PATH = os.path.expanduser("~/Library/Logs/Voca.log")


def _log(message: str) -> None:
    """Append a line to the app log (the app has no console when launched via Finder)."""
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {message}\n")
    except OSError:
        pass


def _traceback() -> str:
    import traceback

    return traceback.format_exc()


def _arm_deadman(seconds: float) -> None:
    """Force a clean process exit after ``seconds``, regardless of what is wedged.

    A daemon timer that calls ``os._exit(0)`` so a stuck background worker (a hung
    paste, a CoreAudio open that never returns, a thread pool that won't drain) can
    never keep the app from quitting. ``os._exit`` is deliberate: it bypasses the
    interpreter shutdown / thread-join that both crashes the app (native threads
    racing exit) and hangs it (concurrent.futures' atexit handler joining a wedged
    worker). If the clean teardown finishes first we ``os._exit`` before this
    fires; the timer is a daemon, so it never keeps the process alive on its own."""
    def _fire():
        _log("deadman: teardown didn't finish in time — force-exiting")
        os._exit(0)

    timer = threading.Timer(seconds, _fire)
    timer.daemon = True
    timer.start()


# Menu-bar icon per engine state. Rendered as monochrome SF Symbol *template*
# images so they sit natively in the menu bar (auto-tinting for light/dark,
# matching the system's own icons) instead of a loud emoji. A `waveform` mark
# reads instantly as "voice"; the busy/recording/error states vary it subtly.
# "ld.waveform" is our OWN 4-bar mark (drawn below), not an SF Symbol: Apple's
# `waveform` symbol has many bars and reads as a *different* logo than the app
# icon's 4-bar waveform (assets/make_icon.py). The idle/ready glyph — the one
# parked in the menu bar whenever the app is running — uses ours so it matches.
_SYMBOL = {
    "loading": "ellipsis",                 # warming the model
    "ready": "ld.waveform",                # idle, waiting for fn (our 4-bar mark)
    "listening": "mic.fill",               # recording your voice
    "transcribing": "ellipsis",            # model is thinking
    "error": "exclamationmark.triangle",   # something went wrong
    "blocked": "exclamationmark.triangle",  # missing a permission
}

# The app icon's 4-bar waveform on a 32-unit grid (identical to make_icon.py and
# the website/dashboard Logo): bar centers + heights, bar width.
_WAVE_CENTERS = (8, 13, 18, 23)
_WAVE_HEIGHTS = (11, 6, 18, 9)
_WAVE_BAR_W = 2.8

# Emoji fallback if SF Symbols aren't available (very old macOS).
_GLYPH = {
    "loading": "⏳",
    "ready": "🎙️",
    "listening": "🔴",
    "transcribing": "✍️",
    "error": "⚠️",
    "blocked": "⚠️",
}

_SYMBOL_CACHE: dict = {}


def _waveform_image():
    """Our 4-bar waveform as a template NSImage, matching the macOS app icon.

    Drawn (not an SF Symbol) because Apple's `waveform` symbol has many bars and
    reads as a different mark. Template image → the menu bar tints it for
    light/dark like a native glyph. Resolution-independent (the handler redraws
    per backing scale), so it stays crisp on Retina. Cached.
    """
    if "ld.waveform" in _SYMBOL_CACHE:
        return _SYMBOL_CACHE["ld.waveform"]

    pad = 1.0
    scale = 14.0 / max(_WAVE_HEIGHTS)        # tallest bar (18u) -> 14 pt
    bar_w = _WAVE_BAR_W * scale
    left_edge = _WAVE_CENTERS[0] - _WAVE_BAR_W / 2.0
    cluster_w = ((_WAVE_CENTERS[-1] + _WAVE_BAR_W / 2.0) - left_edge) * scale
    width = cluster_w + 2 * pad
    height = 16.0
    cy = height / 2.0

    def _draw(_rect):
        try:
            NSColor.blackColor().setFill()  # template: only the shape matters
            for cx, h in zip(_WAVE_CENTERS, _WAVE_HEIGHTS):
                bh = h * scale
                x = pad + ((cx - _WAVE_BAR_W / 2.0) - left_edge) * scale
                y = cy - bh / 2.0
                rect = NSMakeRect(x, y, bar_w, bh)
                NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                    rect, bar_w / 2.0, bar_w / 2.0
                ).fill()
        except Exception:
            return False
        return True

    image = None
    try:
        image = NSImage.imageWithSize_flipped_drawingHandler_(
            NSMakeSize(width, height), False, _draw
        )
        if image is not None:
            image.setTemplate_(True)
    except Exception:
        image = None
    _SYMBOL_CACHE["ld.waveform"] = image
    return image


def _symbol_image(name):
    """A template NSImage for the menu bar (cached), or None if unavailable.

    ``ld.waveform`` is our own drawn 4-bar mark; everything else is an SF Symbol.
    """
    if name == "ld.waveform":
        return _waveform_image()
    if name in _SYMBOL_CACHE:
        return _SYMBOL_CACHE[name]
    image = None
    try:
        image = NSImage.imageWithSystemSymbolName_accessibilityDescription_(name, None)
        if image is not None:
            cfg = NSImageSymbolConfiguration.configurationWithPointSize_weight_(
                15.0, NSFontWeightRegular
            )
            image = image.imageWithSymbolConfiguration_(cfg) or image
            image.setTemplate_(True)  # let the menu bar tint it (light/dark)
    except Exception:
        image = None
    _SYMBOL_CACHE[name] = image
    return image


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
        self.overlay = None
        self._pending = []  # (state, info) queued from worker threads
        self._pending_lock = threading.Lock()
        return self

    # -- UI construction (main thread) --------------------------------------
    @objc.python_method
    def build(self):
        bar = NSStatusBar.systemStatusBar()
        self.statusItem = bar.statusItemWithLength_(NSVariableStatusItemLength)
        self._glyph("loading")

        menu = NSMenu.alloc().init()

        self.stateItem = self._item("Loading model…", None)
        menu.addItem_(self.stateItem)
        self.lastItem = self._item("Last: —", None)
        menu.addItem_(self.lastItem)
        menu.addItem_(NSMenuItem.separatorItem())

        dashboard_item = self._item("Open Dashboard…", "openDashboard:")
        dashboard_item.setKeyEquivalent_("d")
        menu.addItem_(dashboard_item)
        menu.addItem_(NSMenuItem.separatorItem())

        hint = self._item(f"Model: {CONFIG.model.split('/')[-1]}", None)
        menu.addItem_(hint)
        menu.addItem_(NSMenuItem.separatorItem())

        quit_item = self._item("Quit Voca", "quitApp:")
        quit_item.setKeyEquivalent_("q")
        menu.addItem_(quit_item)

        self.statusItem.setMenu_(menu)

        # Heads-up voice overlay that drops from the camera notch while you hold fn.
        self.overlay = Overlay.alloc().initWithLevelProvider_(
            lambda: self.engine.recorder.level
        )
        self.overlay.build()

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
                "Voca needs the microphone to hear you. Turn it on under "
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
                "Voca can hear the fn key but can't paste text yet. "
                "Add it under System Settings → Privacy & Security → Accessibility "
                "(toggle it ON), then quit and relaunch the app.",
            )

        self.hotkey = FnHotkey(
            self.engine.on_press,
            self.engine.on_release,
            log=_log,
            max_hold_seconds=CONFIG.max_record_seconds,
        )
        try:
            # Run the tap on its own thread/run loop, not the main one — the main
            # run loop drives the 60 fps overlay, and sharing it lets that drawing
            # starve the tap so macOS disables it and drops fn presses/releases
            # (the intermittent "chopped into empty fragments" failure).
            self.hotkey.start_background()
            self._observe_wake()  # re-arm the tap the instant the Mac wakes
            _log("fn hotkey installed on dedicated thread — ready to dictate")
        except PermissionError as exc:
            _log(f"BLOCKED: {exc}")
            self._show_state("blocked", "Needs Accessibility permission")
            self._alert(
                "Accessibility permission needed",
                f"{exc}\n\nAdd “Voca” under System Settings → Privacy & "
                "Security → Accessibility, then quit and relaunch the app.",
            )

    @objc.python_method
    def _observe_wake(self):
        """Re-enable the fn tap the moment the Mac wakes from sleep.

        A CGEventTap is frequently disabled across a sleep/wake cycle, and the
        disable event isn't always delivered — the watchdog catches that within a
        second or two, but waking the tap on the wake notification makes recovery
        instant so the first fn press after opening the lid already works.
        """
        nc = NSWorkspace.sharedWorkspace().notificationCenter()
        nc.addObserver_selector_name_object_(
            self, "systemDidWake:", "NSWorkspaceDidWakeNotification", None
        )

    def systemDidWake_(self, _notification):  # noqa: N802 (main thread)
        if self.hotkey is not None:
            self.hotkey.reenable()

    # -- engine state bridge (callable from any thread) ---------------------
    @objc.python_method
    def onEngineState(self, state, info):
        # Keep all data as native Python objects (no ObjC bridging of dicts);
        # just wake the main thread to drain the queue.
        with self._pending_lock:
            self._pending.append((state, dict(info) if info else {}))
        # Deliver in *common* modes so the state (and the overlay it shows) lands
        # even while the run loop is in a tracking mode — e.g. the status-bar menu
        # is open — instead of stalling until the loop returns to its default mode.
        self.performSelectorOnMainThread_withObject_waitUntilDone_modes_(
            "drainStates:", None, False, [NSRunLoopCommonModes]
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
            if self.overlay is not None:
                self.overlay.show()
        elif state == "transcribing":
            self._show_state("transcribing", f"Transcribing {float(g('duration', 0)):0.1f}s…")
            if self.overlay is not None:
                self.overlay.set_mode("thinking")
        elif state == "result":
            text = str(g("text", ""))
            elapsed = float(g("elapsed", 0))
            self.lastItem.setTitle_(f"Last: “{_truncate(text)}”  ({elapsed:0.1f}s)")
            self._show_state("ready", "Inserted ✓")
            if self.overlay is not None:
                self.overlay.set_mode("done")  # brief green confirm before it retracts
        elif state == "empty":
            self._show_state("ready", "Nothing recognized")
        elif state == "error":
            self._show_state("error", f"Error: {_truncate(str(g('error', '')))}")
        elif state == "idle":
            self._glyph("ready")  # leave the status line on its last message
            if self.overlay is not None:
                self.overlay.hide()

    @objc.python_method
    def _show_state(self, glyph_key, message):
        self._glyph(glyph_key)
        if self.stateItem is not None:
            self.stateItem.setTitle_(message)

    @objc.python_method
    def _glyph(self, glyph_key):
        if self.statusItem is None:
            return
        button = self.statusItem.button()
        image = _symbol_image(_SYMBOL.get(glyph_key, "ld.waveform"))
        if image is not None:
            button.setImage_(image)
            button.setTitle_("")  # image-only; no stray text beside the icon
        else:  # SF Symbols unavailable — fall back to the emoji glyph
            button.setImage_(None)
            button.setTitle_(_GLYPH.get(glyph_key, "🎙️"))

    @objc.python_method
    def _alert(self, title, message):
        # Bring the (accessory) app forward first. Without this, an accessory app
        # — no Dock icon, usually not the active app — can open its alert unfocused
        # or behind other windows while runModal blocks the main thread, so the app
        # looks frozen with no visible dialog to dismiss. Activating guarantees the
        # modal is front-most and dismissible.
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        alert = NSAlert.alloc().init()
        alert.setMessageText_(title)
        alert.setInformativeText_(message)
        alert.runModal()

    # -- menu actions -------------------------------------------------------
    def openDashboard_(self, _):  # noqa: N802
        from .launch import open_dashboard

        open_dashboard()

    def quitApp_(self, _):  # noqa: N802
        self._terminate()

    def applicationWillTerminate_(self, _notification):  # noqa: N802
        # Backstop for any other termination route (Cmd-Q, logout, the app menu).
        # Idempotent with quitApp_, so running both is harmless.
        self._terminate()

    @objc.python_method
    def _terminate(self):
        """Quit for good — guaranteed prompt, crash-free, and never frozen.

        Pressing Quit used to hang whenever a background worker was wedged: the old
        path waited (unbounded) for every thread pool to drain on the main thread,
        so one stuck paste / audio open froze the menu and the app could neither
        quit nor restart. Now we:
          1. arm a hard deadman that force-exits the process after a short grace no
             matter what is wedged,
          2. tear down best-effort with bounded waits, then
          3. exit via os._exit — which skips the interpreter / native-thread
             teardown (and the concurrent.futures atexit join of any wedged
             worker) that originally crashed *and* hung the app on quit.
        Either the clean path reaches os._exit in a few ms, or the deadman fires —
        but the process always dies promptly.
        """
        if getattr(self, "_terminating", False):
            return
        self._terminating = True
        _arm_deadman(4.0)
        try:
            self._teardown()
        except Exception:
            _log("terminate: teardown failed\n" + _traceback())
        _log("=== Voca exiting ===")
        os._exit(0)

    @objc.python_method
    def _teardown(self):
        """Stop all background activity in dependency order. Runs once."""
        if getattr(self, "_torn_down", False):
            return
        self._torn_down = True
        # 1. Stop the hotkey first: once its tap + watchdog threads are joined no
        #    new press/release can fire into the engine while we wind it down.
        try:
            if self.hotkey is not None:
                self.hotkey.stop()
        except Exception:
            _log("teardown: hotkey stop failed\n" + _traceback())
        # 2. Stop the overlay's render timer and order the panel out (main thread).
        try:
            if self.overlay is not None:
                self.overlay.teardown()
        except Exception:
            _log("teardown: overlay teardown failed\n" + _traceback())
        # 3. Drain the engine's worker pools and close the mic stream last, so no
        #    capture / transcription / paste is mid-flight at exit.
        try:
            self.engine.shutdown()
        except Exception:
            _log("teardown: engine shutdown failed\n" + _traceback())


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
        # Open the mic stream now (no press can race it — the hotkey isn't installed
        # yet) so the first key-down doesn't pay the cold CoreAudio device-open.
        controller.engine.prewarm_audio()
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
    path = os.path.join(tempfile.gettempdir(), "voca.lock")
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

    _log("=== Voca launching ===")
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
