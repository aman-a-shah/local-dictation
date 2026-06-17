"""Microphone permission handling.

sounddevice/PortAudio talks to the CoreAudio HAL, which on modern macOS returns
**silent zeros** when the app hasn't been granted Microphone access — it does NOT
reliably trigger the permission prompt itself. So we explicitly ask AVFoundation
to request access, which shows the system prompt and registers the app under
System Settings → Privacy & Security → Microphone.
"""

from __future__ import annotations

from AVFoundation import AVCaptureDevice
from ApplicationServices import (
    AXIsProcessTrusted,
    AXIsProcessTrustedWithOptions,
    kAXTrustedCheckOptionPrompt,
)

# AVMediaTypeAudio is the constant "soun"; use the literal to avoid import churn
# across pyobjc versions.
_AUDIO = "soun"

# AVAuthorizationStatus values
NOT_DETERMINED = 0
RESTRICTED = 1
DENIED = 2
AUTHORIZED = 3

_STATUS_NAMES = {0: "not-determined", 1: "restricted", 2: "denied", 3: "authorized"}


def mic_status() -> int:
    return AVCaptureDevice.authorizationStatusForMediaType_(_AUDIO)


def mic_status_name() -> str:
    return _STATUS_NAMES.get(mic_status(), "unknown")


def request_mic(completion) -> None:
    """Prompt for mic access if undetermined. `completion(granted: bool)` runs
    on an arbitrary thread once the user responds (or immediately if already set).
    """
    AVCaptureDevice.requestAccessForMediaType_completionHandler_(_AUDIO, completion)


def accessibility_trusted() -> bool:
    """Whether this app may post synthetic events (needed to paste/⌘V).

    Note this is a *separate* grant from the one that lets us listen for the fn
    key — an app can monitor input yet be unable to post it.
    """
    return bool(AXIsProcessTrusted())


def request_accessibility() -> bool:
    """Same as accessibility_trusted(), but also opens the system prompt that
    deep-links the user to add this app under Accessibility.
    """
    return bool(AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True}))
