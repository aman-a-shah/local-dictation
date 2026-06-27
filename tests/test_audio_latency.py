"""Regression tests for microphone press-to-capture latency.

The bug: pressing fn sometimes took ~half a second to start capturing. The cause
was ``Recorder.start`` calling ``sd.query_devices`` (a synchronous CoreAudio
device query) on every press — both on warm back-to-back presses and, worse,
stacked on top of CoreAudio's stream restart on a cold press after the idle
window. The fix keeps the device query OFF the key-press hot path: warm presses
just flip recording on, cold presses only restart the stream, and the
default-device check moves to ``pause`` (idle, off the hot path).

These tests assert ``start`` never queries the device, and that ``pause`` does.
``sounddevice`` is stubbed so they run with no audio hardware or native dep.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class _FakeStream:
    def __init__(self, **_kw) -> None:
        self.active = False
        self.starts = 0
        self.stops = 0

    def start(self) -> None:
        self.active = True
        self.starts += 1

    def stop(self) -> None:
        self.active = False
        self.stops += 1

    def abort(self, ignore_errors: bool = False) -> None:
        self.active = False

    def close(self, ignore_errors: bool = False) -> None:
        self.active = False


def _make_sd_stub() -> types.ModuleType:
    sd = types.ModuleType("sounddevice")
    sd.query_count = 0
    sd._device = (0, "Built-in Mic")  # what query_devices currently reports

    def query_devices(kind=None):
        sd.query_count += 1
        return {"index": sd._device[0], "name": sd._device[1]}

    sd.query_devices = query_devices
    sd.InputStream = _FakeStream
    return sd


sys.modules.setdefault("sounddevice", _make_sd_stub())

import sounddevice as sd  # noqa: E402  (our stub)
from dictate.audio import Recorder  # noqa: E402


def _queries(fn):
    """Run fn and return how many device queries it caused."""
    before = sd.query_count
    fn()
    return sd.query_count - before


def test_warm_start_never_queries_the_device():
    rec = Recorder()
    rec.prewarm()              # opens the stream (one query, off the hot path)
    rec.start()                # cold: stream exists but inactive -> just start it
    audio, _ = rec.stop()      # stream left running (warm)

    # Back-to-back press within the warm window must not touch the device.
    assert _queries(rec.start) == 0, "warm start re-queried the input device"
    assert rec._stream.active
    rec.close()


def test_cold_start_after_pause_only_restarts_stream():
    rec = Recorder()
    rec.prewarm()
    rec.start()
    rec.stop()
    rec.pause()                # idle release: stops stream + does the device check

    starts_before = rec._stream.starts
    # First press after the idle window: pays the stream restart, NOT a query.
    assert _queries(rec.start) == 0, "cold start re-queried the input device"
    assert rec._stream.starts == starts_before + 1, "cold start did not restart the stream"
    rec.close()


def test_pause_performs_the_device_check_off_the_hot_path():
    rec = Recorder()
    rec.prewarm()
    rec.start()
    rec.stop()
    # The device check the press path used to do now happens here, while idle.
    assert _queries(rec.pause) >= 1, "pause skipped the default-device check"
    assert not rec._stream.active, "pause left the mic stream running"
    rec.close()


def test_device_change_while_idle_is_rebound_by_pause():
    rec = Recorder()
    rec.prewarm()
    rec.start()
    rec.stop()
    old_stream = rec._stream

    sd._device = (1, "AirPods")  # user switched the default input while idle
    rec.pause()                  # pause should notice and rebuild the stream

    assert rec._stream is not old_stream, "pause did not rebind to the new device"
    assert rec._stream_device == (1, "AirPods")
    # And the next cold press still doesn't query — it just starts the new stream.
    assert _queries(rec.start) == 0
    assert rec._stream.active
    rec.close()


if __name__ == "__main__":
    test_warm_start_never_queries_the_device()
    print("✓ warm start never queries")
    test_cold_start_after_pause_only_restarts_stream()
    print("✓ cold start only restarts")
    test_pause_performs_the_device_check_off_the_hot_path()
    print("✓ pause does the device check")
    test_device_change_while_idle_is_rebound_by_pause()
    print("✓ device change rebound at idle")
    print("\nAll audio-latency checks passed.")
