"""Regression tests for the macOS fn (🌐 globe) push-to-talk listener.

The bug these guard against: the activation toggled at random — recording
started when the user had NOT pressed fn, and a real fn press sometimes failed
to start anything. The cause was treating the *global* secondary-fn modifier
(`kCGEventFlagMaskSecondaryFn`) as "the globe key is down". That bit is shared
by the arrow keys, Page Up/Down, Home/End and the function row, so holding any
of them made `_resync()` synthesise a phantom press — which also wedged the
internal `_is_down` flag, swallowing the next genuine press.

The fix: only a real keycode-63 flagsChanged event may start a recording;
`_resync()` is one-directional (it may release a stuck hold, never begin one).

Quartz is stubbed so these run on any platform with no native dependency.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# -- minimal Quartz stub, installed before importing the module under test ----
_SECONDARY_FN = 0x800000


def _make_quartz_stub() -> types.ModuleType:
    q = types.ModuleType("Quartz")
    q.kCGEventFlagMaskSecondaryFn = _SECONDARY_FN
    q.kCGEventTapDisabledByTimeout = 0xFFFFFFFE
    q.kCGEventTapDisabledByUserInput = 0xFFFFFFFF
    q.kCGKeyboardEventKeycode = 9
    q.kCGEventFlagsChanged = 12
    q.kCGSessionEventTap = 1
    q.kCGHeadInsertEventTap = 0
    q.kCGEventTapOptionListenOnly = 1
    q.kCGEventSourceStateCombinedSessionState = 0
    q.kCFRunLoopCommonModes = object()
    q.CGEventMaskBit = lambda bit: 1 << bit
    # Events are plain dicts: {"keycode": int, "flags": int}.
    q.CGEventGetIntegerValueField = lambda event, _field: event["keycode"]
    q.CGEventGetFlags = lambda event: event["flags"]
    # Overridden per-test to script what the (contaminated) global state reads.
    q.CGEventSourceFlagsState = lambda _state: 0
    return q


sys.modules.setdefault("Quartz", _make_quartz_stub())

from dictate.hotkey import FN_KEYCODE, FnHotkey  # noqa: E402


def _hotkey():
    presses: list[int] = []
    releases: list[int] = []
    hk = FnHotkey(
        on_press=lambda: presses.append(1),
        on_release=lambda: releases.append(1),
    )
    return hk, presses, releases


# -- the core regression: phantom presses from shared nav keys ---------------

def test_resync_never_synthesises_a_press_from_the_shared_flag():
    """A held arrow key asserts secondary-fn; resync must NOT start recording."""
    hk, presses, releases = _hotkey()
    hk._secondary_fn_active = lambda: True  # e.g. user is holding an arrow key
    hk._resync()
    assert presses == [], "resync started a recording without a real fn press"
    assert releases == []
    assert hk._is_down is False


def test_real_fn_press_still_works_after_a_phantom_window():
    """The phantom press used to wedge _is_down and swallow the next real press."""
    hk, presses, releases = _hotkey()
    # Nav key held during a tap re-enable: resync runs but must stay inert.
    hk._secondary_fn_active = lambda: True
    hk._resync()
    # Now the user actually presses fn — keycode 63, secondary-fn flag set.
    hk._callback(None, 12, {"keycode": FN_KEYCODE, "flags": _SECONDARY_FN}, None)
    assert presses == [1], "real fn press was swallowed"


# -- resync's one legitimate job: release a hold we can no longer trust -------

def test_resync_releases_a_stuck_hold_when_modifier_is_clear():
    hk, presses, releases = _hotkey()
    hk._callback(None, 12, {"keycode": FN_KEYCODE, "flags": _SECONDARY_FN}, None)
    assert hk._is_down is True
    hk._secondary_fn_active = lambda: False  # fn is genuinely up now
    hk._resync()
    assert releases == [1]
    assert hk._is_down is False


def test_resync_keeps_a_hold_while_modifier_still_active():
    """If fn may still be down, don't chop the utterance on a spurious resync."""
    hk, presses, releases = _hotkey()
    hk._callback(None, 12, {"keycode": FN_KEYCODE, "flags": _SECONDARY_FN}, None)
    hk._secondary_fn_active = lambda: True
    hk._resync()
    assert releases == []
    assert hk._is_down is True


# -- the real-event path: keycode-gated, idempotent --------------------------

def test_callback_ignores_non_fn_keys():
    """Arrow-key flagsChanged (keycode != 63) must never toggle recording."""
    hk, presses, releases = _hotkey()
    for keycode in (123, 124, 125, 126):  # the four arrow keys
        hk._callback(None, 12, {"keycode": keycode, "flags": _SECONDARY_FN}, None)
    assert presses == []
    assert releases == []
    assert hk._is_down is False


def test_callback_press_then_release_round_trip():
    hk, presses, releases = _hotkey()
    hk._callback(None, 12, {"keycode": FN_KEYCODE, "flags": _SECONDARY_FN}, None)
    hk._callback(None, 12, {"keycode": FN_KEYCODE, "flags": 0}, None)
    assert presses == [1]
    assert releases == [1]
    assert hk._is_down is False


def test_callback_double_press_is_idempotent():
    """Two presses with no intervening release fire on_press exactly once."""
    hk, presses, releases = _hotkey()
    hk._callback(None, 12, {"keycode": FN_KEYCODE, "flags": _SECONDARY_FN}, None)
    hk._callback(None, 12, {"keycode": FN_KEYCODE, "flags": _SECONDARY_FN}, None)
    assert presses == [1]


if __name__ == "__main__":
    test_resync_never_synthesises_a_press_from_the_shared_flag()
    print("✓ resync never synthesises a press")
    test_real_fn_press_still_works_after_a_phantom_window()
    print("✓ real press survives a phantom window")
    test_resync_releases_a_stuck_hold_when_modifier_is_clear()
    print("✓ resync releases a stuck hold")
    test_resync_keeps_a_hold_while_modifier_still_active()
    print("✓ resync keeps a live hold")
    test_callback_ignores_non_fn_keys()
    print("✓ non-fn keys ignored")
    test_callback_press_then_release_round_trip()
    print("✓ press/release round trip")
    test_callback_double_press_is_idempotent()
    print("✓ double press idempotent")
    print("\nAll hotkey checks passed.")
