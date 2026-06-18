"""Spawn the dashboard window as a separate process.

Called from the tray / menu-bar "Open Dashboard" action. Running it out-of-process
keeps the resident background app (event tap / tray loop) untouched while the
webview owns its own main loop.
"""

from __future__ import annotations

import os
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
        # Re-launch our own app *bundle* with the --dashboard flag, which the
        # entry point (dictate.main) routes to the dashboard window.
        #
        # We must launch the bundle executable, not sys.executable: under py2app
        # sys.executable is the embedded Python interpreter (it doesn't
        # understand --dashboard and wouldn't set up the bundle's import paths),
        # so the old `[sys.executable, "--dashboard"]` silently exited with
        # "unknown option --dashboard" and the dashboard never opened. py2app
        # exposes the real launcher via $ARGVZERO; PyInstaller's sys.executable
        # already is the launcher, so fall back to it.
        launcher = os.environ.get("ARGVZERO") or sys.executable
        cmd = [launcher, "--dashboard"]
    else:
        cmd = [sys.executable, "-m", "dictate.dashboard_window"]

    try:
        _proc = subprocess.Popen(cmd)
    except Exception as exc:
        print(f"[launch] could not open dashboard: {exc}", flush=True)
