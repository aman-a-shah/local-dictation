"""Microphone access on Windows.

Unlike macOS TCC, Windows desktop (Win32) apps generally have microphone access
by default; access can still be turned off globally under Settings → Privacy &
security → Microphone. We don't get a programmatic prompt, so we expose a light
status check (did an input stream actually deliver audio?) and a helper to open
the relevant Settings page when capture comes back silent.

There is no accessibility-style grant required to synthesize keystrokes on
Windows, so those helpers are no-ops kept for interface parity with macOS.
"""

from __future__ import annotations

# Status constants mirror the macOS module so shared code can compare against them.
NOT_DETERMINED = 0
RESTRICTED = 1
DENIED = 2
AUTHORIZED = 3


def mic_status() -> int:
    # Windows doesn't expose a synchronous per-app status for Win32 apps; assume
    # authorized and rely on a silent-audio heuristic at runtime.
    return AUTHORIZED


def mic_status_name() -> str:
    return "authorized"


def request_mic(completion=None) -> None:
    if completion is not None:
        completion(True)


def open_mic_settings() -> None:
    """Open Windows microphone privacy settings (used when capture is silent)."""
    import os

    try:
        os.startfile("ms-settings:privacy-microphone")  # type: ignore[attr-defined]
    except Exception:
        pass


def accessibility_trusted() -> bool:
    return True  # not required on Windows


def request_accessibility() -> bool:
    return True
