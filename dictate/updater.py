"""Lightweight auto-update check.

On launch (and from the dashboard's "Check for updates" button) the app polls the
website's update endpoint, which returns the latest version + the correct download
URL for this platform/arch. If newer, the UI offers a one-click download that opens
the installer; the user confirms the OS install step. This deliberately avoids a
heavyweight silent-update framework (Sparkle/WinSparkle) — those are a future
enhancement.

The only data sent off-device is the current version, OS, and arch (disclosed in
the privacy policy). Set ``DICTATE_UPDATE_URL`` to point at your own deployment;
``DICTATE_NO_UPDATE_CHECK=1`` disables it entirely.
"""

from __future__ import annotations

import json
import os
import platform
import ssl
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

# Default endpoint — override to your Vercel domain via DICTATE_UPDATE_URL.
DEFAULT_BASE = os.environ.get("DICTATE_UPDATE_URL", "https://localdictation.app")
_TIMEOUT = 6  # seconds; never block the UI for long


def _platform_arch() -> tuple[str, str]:
    system = platform.system()
    os_name = {"Darwin": "mac", "Windows": "windows"}.get(system, system.lower())
    machine = platform.machine().lower()
    arch = "arm64" if machine in ("arm64", "aarch64") else "x64"
    return os_name, arch


def _version_tuple(v: str) -> tuple:
    parts = []
    for chunk in str(v or "0").lstrip("vV").split("-")[0].split("."):
        try:
            parts.append(int(chunk))
        except ValueError:
            parts.append(0)
    return tuple(parts) or (0,)


def check_for_update(current_version: str) -> dict:
    """Return {available, latest, url, notes}. Never raises."""
    if os.environ.get("DICTATE_NO_UPDATE_CHECK") == "1":
        return {"available": False, "disabled": True}

    os_name, arch = _platform_arch()
    query = urllib.parse.urlencode(
        {"platform": os_name, "arch": arch, "version": current_version}
    )
    url = f"{DEFAULT_BASE.rstrip('/')}/api/update?{query}"
    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(url, timeout=_TIMEOUT, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return {"available": False, "error": str(exc)}

    latest = data.get("version", "")
    available = bool(latest) and _version_tuple(latest) > _version_tuple(current_version)
    return {
        "available": available,
        "latest": latest,
        "url": data.get("url", ""),
        "notes": data.get("notes", ""),
    }


def download_and_open(url: str) -> str:
    """Download the installer to a temp file and hand it to the OS to run."""
    suffix = Path(urllib.parse.urlparse(url).path).suffix or ".bin"
    tmp = Path(tempfile.gettempdir()) / f"LocalDictation-update{suffix}"
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(url, timeout=60, context=ctx) as resp, open(tmp, "wb") as fh:
        fh.write(resp.read())

    system = platform.system()
    if system == "Darwin":
        os.system(f'open "{tmp}"')
    elif system == "Windows":
        os.startfile(str(tmp))  # type: ignore[attr-defined]
    else:
        os.system(f'xdg-open "{tmp}"')
    return str(tmp)
