"""Tiny audio cues so you know the engine's state without looking.

System sounds are preloaded once (loading on each play adds latency and can drop
the first cue). All playback is a no-op when DICTATE_SOUND=0.
"""

from __future__ import annotations

from AppKit import NSSound

from .config import CONFIG


class Feedback:
    def __init__(self) -> None:
        self._sounds: dict[str, object] = {}
        if CONFIG.sound_feedback:
            for key, name in {"start": "Tink", "done": "Pop", "error": "Basso"}.items():
                snd = NSSound.soundNamed_(name)
                if snd is not None:
                    self._sounds[key] = snd

    def _play(self, key: str) -> None:
        snd = self._sounds.get(key)
        if snd is None:
            return
        if snd.isPlaying():
            snd.stop()
        snd.play()

    def listening(self) -> None:
        self._play("start")

    def done(self) -> None:
        self._play("done")

    def error(self) -> None:
        self._play("error")
