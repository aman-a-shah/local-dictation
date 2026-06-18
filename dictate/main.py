"""Unified entry point for the packaged apps.

Dispatches to the right front-end:
- ``--dashboard``         -> the webview dashboard window (spawned by the tray).
- macOS                   -> the native menu-bar app (rich SF Symbols + overlay).
- Windows / Linux         -> the pystray tray app.

The CLI front-end (live console output) remains at ``python -m dictate``.
"""

from __future__ import annotations

import platform
import sys


def main() -> int:
    if "--dashboard" in sys.argv:
        from .dashboard_window import main as dashboard_main

        return dashboard_main()

    system = platform.system()
    if system == "Darwin":
        from .menu_app import main as mac_main

        return mac_main()
    if system == "Windows":
        from .platforms.windows.app import main as win_main

        return win_main()

    # Linux / other: fall back to the tray app (pystray supports it).
    from .platforms.windows.app import main as tray_main

    return tray_main()


if __name__ == "__main__":
    raise SystemExit(main())
