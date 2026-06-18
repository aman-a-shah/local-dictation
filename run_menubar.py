"""py2app entry point for the menu-bar app.

Dispatches through ``dictate.main`` (same as the PyInstaller ``run_app.py``) so
flags like ``--dashboard`` are honored when the bundle re-launches itself. With
no flags on macOS this lands on the native menu-bar app.
"""

from dictate.main import main

if __name__ == "__main__":
    raise SystemExit(main())
