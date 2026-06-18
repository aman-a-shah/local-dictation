"""Spawn the dashboard window as a separate process.

Called from the tray / menu-bar "Open Dashboard" action. Running it out-of-process
keeps the resident background app (event tap / tray loop) untouched while the
webview owns its own main loop.
"""

from __future__ import annotations

import subprocess
import sys

# Track the most recent dashboard process so repeated clicks focus rather than
# stack up windows (best-effort; the OS may have closed it already).
_proc: subprocess.Popen | None = None


def open_dashboard() -> None:
    global _proc
    if _proc is not None and _proc.poll() is None:
        return  # already open

    if getattr(sys, "frozen", False):
        # The frozen app re-invokes itself with a flag the entry point handles.
        cmd = [sys.executable, "--dashboard"]
    else:
        cmd = [sys.executable, "-m", "dictate.dashboard_window"]

    try:
        _proc = subprocess.Popen(cmd)
    except Exception as exc:
        print(f"[launch] could not open dashboard: {exc}", flush=True)
