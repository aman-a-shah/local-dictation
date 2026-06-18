"""Terminal front-end: run dictation with live status printed to the console.

Thin wrapper over DictationEngine — it just renders engine states as console
lines and drives the fn-key tap on its own run loop. For the background menu-bar
version see ``dictate.menu_app``.
"""

from __future__ import annotations

import sys
from typing import Optional

from .config import CONFIG
from .core import DictationEngine
from .platforms import hotkey_label, make_hotkey

_CLEAR = "\r" + " " * 60 + "\r"


def _render(state: str, info: Optional[dict]) -> None:
    info = info or {}
    if state == "listening":
        print("\r🎙️  listening…", end="", flush=True)
    elif state == "transcribing":
        print(f"\r⏳ transcribing {info.get('duration', 0):0.1f}s…", end="", flush=True)
    elif state == "result":
        speed = info["duration"] / info["elapsed"] if info["elapsed"] > 0 else 0.0
        print(f"{_CLEAR}✅ {info['elapsed']:0.2f}s ({speed:0.1f}× realtime)  “{info['text']}”", flush=True)
    elif state == "empty":
        print(f"{_CLEAR}🤷 (nothing recognized)", flush=True)
    elif state == "error":
        print(f"{_CLEAR}❌ {info.get('error', 'transcription failed')}", flush=True)


class DictationApp:
    def __init__(self) -> None:
        self.engine = DictationEngine(on_state=_render)
        self._hotkey = make_hotkey(
            self.engine.on_press, self.engine.on_release, on_cancel=self.engine.cancel
        )

    def run(self) -> None:
        print(f"Loading model: {self.engine.transcriber.model_name}", flush=True)
        elapsed = self.engine.warmup()
        print(f"Model ready in {elapsed:0.1f}s.\n", flush=True)
        key = hotkey_label()
        print(
            "┌──────────────────────────────────────────────┐\n"
            f"│  Hold  {key}  and speak. Release to insert.\n"
            "│  Press Ctrl-C in this window to quit.\n"
            "└──────────────────────────────────────────────┘\n",
            flush=True,
        )
        try:
            self._hotkey.run()
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        print("\nShutting down…", flush=True)
        self.engine.shutdown()


def main() -> int:
    app = DictationApp()
    try:
        app.run()
    except PermissionError as exc:
        print(f"\n⚠️  {exc}\n", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0
    return 0
