"""Whisper transcription via Apple MLX (Metal-accelerated, Apple Silicon only).

Near large-v3 quality at a fraction of the compute, typically 10-20x faster than
real time on M-series. Only importable on Apple Silicon, so the factory guards
its use behind an availability check.

Optional *fast encoder* (``DICTATE_FAST_ENCODER=1``): Whisper's encoder always
runs over a fixed 30 s window, so a 2 s clip pays the same ~1.5 s encoder pass as
a 25 s one. When enabled we shrink that window to just past the actual speech,
cutting ~0.5-0.7 s off most takes. Less context can occasionally flip a hard word
on short audio, so it is off by default and any runaway-repetition / garbage
output is detected and transparently re-run at full context.
"""

from __future__ import annotations

import zlib

import numpy as np

from ..config import CONFIG
from .base import BaseTranscriber


def _is_degenerate(text: str) -> bool:
    """True if `text` looks like a context-starved decode failure.

    Two failure modes show up when the encoder window is shrunk too far for a
    given clip: runaway repetition ("the fox the fox the fox…") and pure-symbol
    garbage (".!!!!!"). Both are easy to spot and are the cue to retry at full
    context. Normal transcripts (even short ones) never trip these.
    """
    t = (text or "").strip()
    if not t:
        return False  # empty is a legitimate result; full context would agree
    if not any(c.isalnum() for c in t):
        return True  # only punctuation/symbols
    comp = len(zlib.compress(t.encode("utf-8")))
    return comp > 0 and len(t) / comp > 2.4  # high ratio == very repetitive


class _DynamicEncoder:
    """Wraps Whisper's AudioEncoder to process only the real speech, not 30 s.

    mlx_whisper always zero-pads each mel segment to the full 30 s window before
    the encoder, so the tail of a short clip is just padding. We trim that
    padding (keeping a margin), run the convs + transformer over the shorter
    sequence, and slice the (positional) sinusoids to match — the encoder output
    for the real frames is unchanged, there's simply far less of it to compute.

    Forwards every other attribute to the real encoder, so it is a drop-in
    replacement for ``model.encoder``. Set ``enabled = False`` to fall straight
    through to full-window behaviour (used for the degenerate-output retry).
    """

    def __init__(self, encoder, min_frames: int, margin_frames: int) -> None:
        self._enc = encoder
        self._pe = encoder._positional_embedding
        self._min_frames = int(min_frames)
        self._margin = int(margin_frames)
        self.enabled = True

    def __getattr__(self, name):  # forward conv1/blocks/etc. for any other caller
        return getattr(self._enc, name)

    def __call__(self, x):
        import mlx.core as mx
        import mlx.nn as nn
        from mlx_whisper.audio import N_FRAMES

        if self.enabled and x.shape[1] >= N_FRAMES:
            # Find the last non-padding mel frame (padding is exact zeros from
            # pad_or_trim); keep everything up to there plus a margin and a floor.
            energy = mx.abs(x).sum(axis=-1)[0]
            nz = np.nonzero(np.asarray(energy > 0))[0]
            content = int(nz[-1]) + 1 if nz.size else x.shape[1]
            window = min(N_FRAMES, max(self._min_frames, content + self._margin))
            if window & 1:  # conv2 has stride 2 — keep the length even
                window += 1
            if window < x.shape[1]:
                x = x[:, :window, :]

        h = nn.gelu(self._enc.conv1(x))
        h = nn.gelu(self._enc.conv2(h))
        h = h + self._pe[: h.shape[1]]
        for block in self._enc.blocks:
            h, _, _ = block(h)
        return self._enc.ln_post(h)


# Mel frames per second of audio (16 kHz / 160-sample hop). Used to convert the
# configured minimum-context seconds into encoder frames.
_FRAMES_PER_SECOND = 100
_MARGIN_FRAMES = 150  # ~1.5 s of context kept after the last detected speech


class MLXTranscriber(BaseTranscriber):
    backend = "mlx"

    def __init__(self) -> None:
        self.model_name = CONFIG.mlx_model
        self._fast = CONFIG.fast_encoder
        self._dynamic = None  # the _DynamicEncoder wrapper, once installed

    def _ensure_fast_encoder(self) -> None:
        """Install the dynamic-context encoder on the cached model (once)."""
        if not self._fast or self._dynamic is not None:
            return
        try:
            import mlx.core as mx
            from mlx_whisper.transcribe import ModelHolder

            model = ModelHolder.get_model(self.model_name, mx.float16)
            if isinstance(model.encoder, _DynamicEncoder):
                self._dynamic = model.encoder  # already wrapped (shared cache)
                return
            min_frames = int(CONFIG.fast_encoder_min_seconds * _FRAMES_PER_SECOND)
            self._dynamic = _DynamicEncoder(model.encoder, min_frames, _MARGIN_FRAMES)
            model.encoder = self._dynamic
        except Exception as exc:  # never let an optimization break transcription
            print(f"[mlx] fast encoder unavailable: {exc}", flush=True)
            self._fast = False

    def warmup(self) -> None:
        self._ensure_fast_encoder()
        silence = np.zeros(CONFIG.sample_rate, dtype=np.float32)
        try:
            self._run(silence)
        except Exception as exc:  # pragma: no cover - best effort
            print(f"[mlx] warmup skipped: {exc}", flush=True)

    def _transcribe(self, audio: np.ndarray) -> str:
        import mlx_whisper

        result = mlx_whisper.transcribe(
            audio,
            path_or_hf_repo=self.model_name,
            language=self.language,
            # Dictation clips are independent thoughts; don't condition on prior
            # text (faster, avoids repetition loops).
            condition_on_previous_text=False,
            temperature=0.0,  # greedy/deterministic = fastest + most stable
            fp16=True,
            verbose=None,
        )
        return result.get("text", "")

    def _run(self, audio: np.ndarray) -> str:
        self._ensure_fast_encoder()
        text = self._transcribe(audio)
        # Shrinking the window can rarely produce a context-starved degenerate
        # decode; when it does, redo this one clip at full context so quality is
        # never worse than the standard path.
        if self._fast and self._dynamic is not None and _is_degenerate(text):
            self._dynamic.enabled = False
            try:
                text = self._transcribe(audio)
            finally:
                self._dynamic.enabled = True
        return text


def available() -> bool:
    """True only on Apple Silicon with mlx-whisper importable."""
    import platform

    if platform.system() != "Darwin" or platform.machine() != "arm64":
        return False
    try:
        import mlx_whisper  # noqa: F401
    except Exception:
        return False
    return True
