"""PyInstaller entry point for the packaged cross-platform app.

This is the script PyInstaller freezes (see desktop/pyinstaller/). It dispatches
to the menu-bar app (macOS) / tray app (Windows) / dashboard window via
``dictate.main``. The legacy py2app build still uses ``run_menubar.py``.
"""

from dictate.main import main

if __name__ == "__main__":
    raise SystemExit(main())
