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
    if "--selftest" in sys.argv:
        return _selftest()

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


def _selftest() -> int:
    """Import every critical module + construct the transcriber/store.

    Used as a packaging smoke test in CI: a frozen build that can import all its
    bundled deps and pick a backend exits 0. Does NOT load model weights or open
    any UI, so it runs headless on a CI runner.
    """
    try:
        from . import bridge, core, paths, store, updater  # noqa: F401
        from .backends.factory import create_transcriber
        from .platforms import inject, make_hotkey  # noqa: F401

        t = create_transcriber()
        store.get_store().stats()
        print(f"selftest OK: backend={t.backend} model={t.model_name} data={paths.data_dir()}")
        return 0
    except Exception:
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
