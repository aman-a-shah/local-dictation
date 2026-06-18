"""The Python <-> JS API exposed to the dashboard webview.

Methods here are callable from the dashboard front-end via pywebview's js_api
bridge (``window.pywebview.api.get_stats()`` etc.). Everything is local: it reads
the SQLite history and the on-disk settings, and writes settings back. No network.

Return values are plain JSON-serializable dicts/lists so they cross the bridge
cleanly.
"""

from __future__ import annotations

import json
from typing import Any

from .config import CONFIG
from .paths import settings_path
from .store import get_store


# Settings the dashboard is allowed to read/write. Backed by settings.json; the
# engine reads env/CONFIG at process start, so most take effect on next launch
# (the UI tells the user when a restart is needed).
_DEFAULT_SETTINGS = {
    "language": CONFIG.language or "auto",
    "hotkey": CONFIG.hotkey,
    "polish": CONFIG.polish,
    "list_style": CONFIG.list_style,
    "sound_feedback": CONFIG.sound_feedback,
    "append_space": CONFIG.append_space,
    "restore_clipboard": CONFIG.restore_clipboard,
    "save_history": CONFIG.save_history,
    "run_at_login": False,
}


def _load_settings() -> dict:
    path = settings_path()
    data = dict(_DEFAULT_SETTINGS)
    try:
        if path.exists():
            data.update(json.loads(path.read_text(encoding="utf-8")))
    except Exception:
        pass
    return data


def _save_settings(values: dict) -> dict:
    data = _load_settings()
    data.update({k: v for k, v in (values or {}).items() if k in _DEFAULT_SETTINGS})
    settings_path().write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


class DashboardAPI:
    """Instance bound to a pywebview window as ``js_api``."""

    def __init__(self, app_version: str = "", on_quit=None, on_open_settings=None) -> None:
        self._version = app_version
        self._on_quit = on_quit

    # -- stats + history ----------------------------------------------------
    def get_stats(self) -> dict[str, Any]:
        return get_store().stats()

    def get_recent(self, limit: int = 50, offset: int = 0) -> list[dict]:
        return get_store().recent(int(limit), int(offset))

    def search(self, query: str, limit: int = 50) -> list[dict]:
        return get_store().search(str(query or ""), int(limit))

    def delete_item(self, item_id: int) -> bool:
        get_store().delete(int(item_id))
        return True

    def clear_history(self) -> bool:
        get_store().clear()
        return True

    def copy_text(self, item_id: int) -> str:
        item = get_store().get(int(item_id))
        text = (item or {}).get("text", "")
        try:
            from .platforms import inject  # reuse the clipboard layer
            # Just put it on the clipboard without pasting.
            import sys

            if sys.platform == "darwin":
                from AppKit import NSPasteboard, NSPasteboardTypeString

                pb = NSPasteboard.generalPasteboard()
                pb.clearContents()
                pb.setString_forType_(text, NSPasteboardTypeString)
            else:
                import pyperclip

                pyperclip.copy(text)
        except Exception:
            pass
        return text

    # -- settings -----------------------------------------------------------
    def get_settings(self) -> dict:
        return _load_settings()

    def set_settings(self, values: dict) -> dict:
        return _save_settings(values)

    # -- app/meta -----------------------------------------------------------
    def get_meta(self) -> dict:
        import platform as _p

        from .platforms import SYSTEM, hotkey_label

        return {
            "version": self._version,
            "platform": SYSTEM,
            "arch": _p.machine(),
            "hotkey_label": hotkey_label(),
        }

    def check_update(self) -> dict:
        try:
            from .updater import check_for_update

            return check_for_update(self._version)
        except Exception as exc:
            return {"available": False, "error": str(exc)}

    def quit_app(self) -> bool:
        if self._on_quit:
            self._on_quit()
        return True
