"""Audio cues on Windows via the built-in winsound system sounds.

Mirrors the macOS Feedback API (listening/done/error) so the engine is identical
across platforms. All playback is a no-op when DICTATE_SOUND=0 or winsound is
unavailable.
"""

from __future__ import annotations

from ...config import CONFIG


class Feedback:
    def __init__(self) -> None:
        self._enabled = CONFIG.sound_feedback
        try:
            import winsound  # noqa: F401

            self._winsound = winsound
        except Exception:
            self._winsound = None
            self._enabled = False

    def _play(self, alias: str) -> None:
        if not self._enabled or self._winsound is None:
            return
        try:
            # Asynchronous so it never blocks the hotkey/worker thread.
            self._winsound.PlaySound(
                alias, self._winsound.SND_ALIAS | self._winsound.SND_ASYNC
            )
        except Exception:
            pass

    def listening(self) -> None:
        self._play("SystemAsterisk")

    def done(self) -> None:
        self._play("SystemDefault")

    def error(self) -> None:
        self._play("SystemHand")
