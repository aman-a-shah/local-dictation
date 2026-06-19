"""Shared transcription primitives + the backend interface.

Silence trimming and hallucination cleanup are model-agnostic, so they live here
and are reused by every backend. A concrete backend only has to implement
``_run`` (raw audio -> text) and ``warmup``.
"""

from __future__ import annotations

import abc

import numpy as np

from ..config import CONFIG


def trim_silence(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    """Drop leading/trailing near-silence using a short-window energy gate.

    The threshold is anchored to the clip's own **noise floor** (the quietest
    windows), not to a fixed level or a fraction of the peak. That distinction is
    critical: with a quiet or far-field mic, real speech — especially a sentence
    trailing off in volume at the end — sits well below any fixed floor, so the
    old ``max(peak*0.06, 0.0025)`` rule silently chopped the last words off
    ("stop at 20s, only get 10s"). Anchoring to the noise floor keeps every
    window that is audibly above the room, regardless of absolute loudness, and a
    generous pad guards word onsets/offsets. It still trims genuine silence, so
    the latency benefit (Whisper cost scales with length) is preserved.
    """
    if audio.size == 0:
        return audio

    win = max(1, sample_rate // 50)  # 20 ms windows
    n_windows = audio.size // win
    if n_windows < 3:
        return audio

    trimmed = audio[: n_windows * win].reshape(n_windows, win)
    rms = np.sqrt(np.mean(trimmed**2, axis=1) + 1e-9)
    noise = float(np.percentile(rms, 10))   # ambient room/mic noise estimate
    peak = float(rms.max())
    # A hair above the noise floor keeps quiet trailing speech; the tiny
    # peak-relative and absolute terms just guard pathological inputs.
    threshold = max(noise * 1.6, peak * 0.015, 1e-4)
    voiced = np.where(rms > threshold)[0]
    if voiced.size == 0:
        return audio  # all quiet -> let Whisper decide (likely empty)

    pad = 10  # ~200 ms of context on each side (never clip a word edge)
    start = max(0, voiced[0] - pad) * win
    end = min(n_windows, voiced[-1] + 1 + pad) * win
    return audio[start:end]


def has_speech(audio: np.ndarray, sample_rate: int) -> bool:
    """Fast pre-check: does this clip contain any speech at all?

    The expensive path is running Whisper on a *silent* clip — `normalize`
    amplifies the room tone up to 50x and the greedy decoder then spends 1.5-5 s
    hallucinating a stock phrase ("Thank you.") that we throw away. So when the
    user holds the key but says nothing, we want to skip the model entirely.

    The test is the clip's **own dynamic range**, never an absolute level:
    speech makes the loudest 20 ms window tower over the clip's noise floor (the
    quietest windows — inter-word gaps, pre-roll, the release tail), whereas
    stationary room tone has almost no spread (loudest window ~1-2x the floor).
    Being scale-invariant, it's correct for a very quiet mic, where any fixed
    threshold would wrongly discard real speech. The ratio bar (2.5x) sits far
    below speech's typical 5-10x and well above room tone, so it only ever fires
    on clear silence — a borderline clip still falls through to Whisper.
    """
    if audio.size == 0:
        return False
    win = max(1, sample_rate // 50)  # 20 ms windows
    n_windows = audio.size // win
    if n_windows < 3:
        return True  # too short to judge the dynamic range — let the model decide
    w = audio[: n_windows * win].reshape(n_windows, win)
    rms = np.sqrt(np.mean(w**2, axis=1) + 1e-9)
    noise = float(np.percentile(rms, 10))  # the clip's own noise floor
    peak = float(rms.max())
    return peak > noise * 2.5 + 1e-6  # +eps: digital silence (peak==noise==~0) -> False


def normalize(audio: np.ndarray, target_rms: float = 0.08, max_gain: float = 50.0) -> np.ndarray:
    """Bring a quiet capture up to a healthy loudness before transcription.

    A quiet mic (the log shows RMS ~0.0015, vs ~0.08 for a close mic) gives
    Whisper a weak, low-SNR signal: it decodes slower and is far likelier to drop
    or cut short trailing segments. Scaling to a consistent target RMS makes
    transcription both faster and more complete, with a gain cap so pure silence
    isn't blown up and a peak guard so we never clip.
    """
    if audio.size == 0:
        return audio
    rms = float(np.sqrt(np.mean(audio**2)))
    if rms < 1e-6:
        return audio  # silence — nothing to normalize
    gain = min(target_rms / rms, max_gain)
    out = audio * gain
    peak = float(np.abs(out).max())
    if peak > 0.97:
        out = out * (0.97 / peak)
    return out.astype(np.float32, copy=False)


# Backwards-compatible alias (the original lived in transcriber.py as _trim_silence).
_trim_silence = trim_silence


_HALLUCINATIONS = {
    "thank you.",
    "thanks for watching!",
    "you",
    ".",
    "[blank_audio]",
    "(silence)",
}


def clean(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    # Whisper emits stock phrases on pure silence; drop the well-known ones.
    if text.lower() in _HALLUCINATIONS:
        return ""
    return text


_clean = clean


class BaseTranscriber(abc.ABC):
    """Common scaffolding: trim -> run -> clean. Subclasses implement ``_run``."""

    #: Human-readable name of the loaded model (for UI/status lines).
    model_name: str = ""
    #: Short backend id ("mlx" / "faster-whisper") for diagnostics + the dashboard.
    backend: str = "base"

    @property
    def language(self) -> str | None:
        return CONFIG.language or None

    @abc.abstractmethod
    def warmup(self) -> None:
        """Force model load + kernel compilation so the first real take is fast."""

    @abc.abstractmethod
    def _run(self, audio: np.ndarray) -> str:
        """Transcribe already-trimmed audio to raw (uncleaned) text."""

    def transcribe(self, audio: np.ndarray) -> str:
        if audio.size == 0:
            return ""
        audio = trim_silence(audio, CONFIG.sample_rate)
        if audio.size == 0:
            return ""
        audio = normalize(audio)  # consistent loudness -> faster + more complete
        return clean(self._run(audio))
