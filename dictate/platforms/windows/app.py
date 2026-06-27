"""Background tray app for Windows.

The counterpart to the macOS menu-bar app (``dictate.menu_app``): a system-tray
icon that drives the same DictationEngine. Hold the push-to-talk key (default Left
Ctrl), speak, release — text is pasted at the cursor. The tray menu shows status
and the last result, opens the dashboard, and quits.

pystray owns the main thread (``icon.run()``); the hotkey listener and the model
warmup run on their own threads, and engine state callbacks (also off-thread) just
update the tray title/menu.
"""

from __future__ import annotations

import socket
import threading

from ...config import CONFIG
from ...core import DictationEngine
from ...launch import open_dashboard
from ...paths import log_path

_LOG = log_path()

# Tray tooltip per engine state.
_STATUS = {
    "loading": "Voca — loading model…",
    "ready": "Voca — ready (hold {key})",
    "listening": "Voca — listening…",
    "transcribing": "Voca — transcribing…",
    "error": "Voca — error",
}


def _log(message: str) -> None:
    try:
        import time

        with open(_LOG, "a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {message}\n")
    except OSError:
        pass


def _single_instance() -> bool:
    """True if we acquired the lock; False if another instance holds it.

    Binds an abstract-ish localhost port as a cross-process mutex (no file
    cleanup needed; the socket frees on process exit).
    """
    global _LOCK_SOCK
    _LOCK_SOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _LOCK_SOCK.bind(("127.0.0.1", 50573))
        _LOCK_SOCK.listen(1)
        return True
    except OSError:
        return False


_LOCK_SOCK = None


def _make_icon_image():
    """A simple waveform glyph for the tray (generated, no asset dependency)."""
    from PIL import Image, ImageDraw

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 4-bar waveform matching the brand mark (web/public/favicon.svg): heights
    # 11/6/18/9 on the 32-grid, normalized to the tallest bar.
    bars = [11 / 18, 6 / 18, 1.0, 9 / 18]
    n = len(bars)
    bw = 5
    gap = (size - n * bw) // (n + 1)
    for i, h in enumerate(bars):
        x = gap + i * (bw + gap)
        bar_h = int(h * (size - 18))
        y0 = (size - bar_h) // 2
        d.rounded_rectangle([x, y0, x + bw, y0 + bar_h], radius=2, fill=(124, 92, 255, 255))
    return img


class TrayApp:
    def __init__(self) -> None:
        self.engine = DictationEngine(on_state=self._on_state)
        self.icon = None
        self.hotkey = None
        self._last = "—"
        self._state_title = _STATUS["loading"]

    # -- engine -> tray -----------------------------------------------------
    def _on_state(self, state, info=None):
        info = info or {}
        key = CONFIG.hotkey
        if state in _STATUS:
            self._state_title = _STATUS[state].format(key=key)
        if state == "result":
            text = str(info.get("text", ""))
            self._last = (text[:60] + "…") if len(text) > 60 else text
            self._state_title = _STATUS["ready"].format(key=key)
        if self.icon is not None:
            self.icon.title = self._state_title
            try:
                self.icon.update_menu()
            except Exception:
                pass

    # -- menu ---------------------------------------------------------------
    def _build_menu(self):
        from pystray import Menu, MenuItem

        return Menu(
            MenuItem(lambda _i: self._state_title, None, enabled=False),
            MenuItem(lambda _i: f"Last: {self._last}", None, enabled=False),
            Menu.SEPARATOR,
            MenuItem("Open Dashboard", lambda _i, _it: open_dashboard(), default=True),
            Menu.SEPARATOR,
            MenuItem("Quit", lambda _i, _it: self._quit()),
        )

    def _quit(self):
        # Stop the push-to-talk listener first so no press/release can fire into
        # the engine while we wind it down, then drain the engine, then end the
        # tray loop — the same clean ordering the macOS app uses on quit.
        if self.hotkey is not None:
            stop = getattr(self.hotkey, "stop", None)
            if callable(stop):
                try:
                    stop()
                except Exception:
                    pass
        try:
            self.engine.shutdown()
        finally:
            if self.icon is not None:
                self.icon.stop()

    # -- lifecycle ----------------------------------------------------------
    def _warmup_and_hook(self):
        from ...platforms import make_hotkey

        try:
            _log("warming up model…")
            elapsed = self.engine.warmup()
            _log(f"model ready in {elapsed:0.1f}s")
            self.hotkey = make_hotkey(
                self.engine.on_press,
                self.engine.on_release,
                log=_log,
                on_cancel=self.engine.cancel,
            )
            self.hotkey.start_background()
            _log("push-to-talk hooked — ready to dictate")
        except Exception:
            import traceback

            _log("FATAL during warmup/hook:\n" + traceback.format_exc())

    def run(self):
        import pystray

        self.icon = pystray.Icon(
            "voca",
            icon=_make_icon_image(),
            title=self._state_title,
            menu=self._build_menu(),
        )
        threading.Thread(target=self._warmup_and_hook, daemon=True).start()
        self.icon.run()  # blocks the main thread


def main() -> int:
    _log("=== Voca (Windows) launching ===")
    if not _single_instance():
        _log("another instance is already running — exiting")
        return 0
    TrayApp().run()
    return 0
