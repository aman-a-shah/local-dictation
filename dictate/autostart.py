"""Enable/disable launch-at-login, per OS.

- macOS:   a LaunchAgent plist in ``~/Library/LaunchAgents``.
- Windows: a value under ``HKCU\\…\\CurrentVersion\\Run``.
- Linux:   a ``.desktop`` file in ``~/.config/autostart``.

This is meaningful for an installed/frozen app; in a dev checkout we still write
the entry but point it at the current interpreter (``python -m dictate``), which
is enough to test the toggle. The ``run_at_login`` setting is applied through here
whenever the dashboard writes settings (see :mod:`dictate.bridge`).
"""

from __future__ import annotations

import platform
import sys
from pathlib import Path

_LABEL = "com.voca.app"  # macOS LaunchAgent label / Linux desktop id
_DISPLAY = "Voca"  # Windows Run value name / desktop Name


def _launch_command() -> list[str]:
    """The argv that starts the resident (tray / menu-bar) app."""
    if getattr(sys, "frozen", False):
        # Frozen build: sys.executable is the bundle/exe launcher itself.
        return [sys.executable]
    # Dev checkout: run the package with the current interpreter.
    return [sys.executable, "-m", "dictate"]


def _macos_app_path() -> str | None:
    """Path to the enclosing ``.app`` bundle, if we're running inside one."""
    for parent in Path(sys.executable).resolve().parents:
        if parent.suffix == ".app":
            return str(parent)
    return None


def _macos_set(enabled: bool) -> None:
    plist = Path.home() / "Library" / "LaunchAgents" / f"{_LABEL}.plist"
    if not enabled:
        plist.unlink(missing_ok=True)
        return
    plist.parent.mkdir(parents=True, exist_ok=True)
    app = _macos_app_path()
    args = ["/usr/bin/open", "-a", app] if app else _launch_command()
    items = "".join(f"\n      <string>{a}</string>" for a in args)
    plist.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0"><dict>\n'
        f"  <key>Label</key><string>{_LABEL}</string>\n"
        f"  <key>ProgramArguments</key><array>{items}\n  </array>\n"
        "  <key>RunAtLoad</key><true/>\n"
        "</dict></plist>\n",
        encoding="utf-8",
    )


def _windows_set(enabled: bool) -> None:
    import winreg

    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_SET_VALUE,
    )
    try:
        if enabled:
            cmd = _launch_command()
            value = " ".join(f'"{c}"' if " " in c else c for c in cmd)
            winreg.SetValueEx(key, _DISPLAY, 0, winreg.REG_SZ, value)
        else:
            try:
                winreg.DeleteValue(key, _DISPLAY)
            except FileNotFoundError:
                pass
    finally:
        winreg.CloseKey(key)


def _linux_set(enabled: bool) -> None:
    desktop = Path.home() / ".config" / "autostart" / f"{_DISPLAY}.desktop"
    if not enabled:
        desktop.unlink(missing_ok=True)
        return
    desktop.parent.mkdir(parents=True, exist_ok=True)
    exec_cmd = " ".join(_launch_command())
    desktop.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={_DISPLAY}\n"
        f"Exec={exec_cmd}\n"
        "X-GNOME-Autostart-enabled=true\n",
        encoding="utf-8",
    )


def set_run_at_login(enabled: bool) -> bool:
    """Apply the launch-at-login setting. Returns True on success, never raises."""
    try:
        system = platform.system()
        if system == "Darwin":
            _macos_set(enabled)
        elif system == "Windows":
            _windows_set(enabled)
        else:
            _linux_set(enabled)
        return True
    except Exception:
        return False
