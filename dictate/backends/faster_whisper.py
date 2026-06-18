"""Whisper transcription via faster-whisper (CTranslate2).

The cross-platform workhorse: runs on Windows and Intel Macs (CPU) and on NVIDIA
GPUs (CUDA). Quantized int8 on CPU keeps a small/distil model responsive; on a
CUDA device we use float16 and a larger model. This backend powers every
non-Apple-Silicon install and is the universal fallback.
"""

from __future__ import annotations

import numpy as np

from ..config import CONFIG
from .base import BaseTranscriber


def _pick_device() -> tuple[str, str]:
    """Return (device, compute_type), honoring config overrides, else autodetect."""
    device = CONFIG.fw_device
    compute = CONFIG.fw_compute_type

    if device == "auto":
        device = "cpu"
        try:  # CUDA is a big win when present; cheap to probe.
            import ctranslate2

            if ctranslate2.get_cuda_device_count() > 0:
                device = "cuda"
        except Exception:
            pass

    if not compute:
        compute = "float16" if device == "cuda" else "int8"
    return device, compute


def _pick_model(device: str) -> str:
    """Resolve the model name. 'auto' picks quality-vs-speed by device."""
    model = CONFIG.fw_model
    if model and model != "auto":
        return model
    # CPU: a distil/small model stays snappy. CUDA: full large-v3-turbo.
    return "deepdml/faster-whisper-large-v3-turbo-ct2" if device == "cuda" else "small.en"


class FasterWhisperTranscriber(BaseTranscriber):
    backend = "faster-whisper"

    def __init__(self) -> None:
        self.device, self.compute_type = _pick_device()
        self.model_name = _pick_model(self.device)
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
                download_root=str(_model_cache_dir()),
            )
        return self._model

    def warmup(self) -> None:
        silence = np.zeros(CONFIG.sample_rate, dtype=np.float32)
        try:
            self._run(silence)
        except Exception as exc:  # pragma: no cover - best effort
            print(f"[faster-whisper] warmup skipped: {exc}", flush=True)

    def _run(self, audio: np.ndarray) -> str:
        model = self._ensure_model()
        # faster-whisper wants float32 @ 16 kHz, which is exactly what we capture.
        segments, _info = model.transcribe(
            audio,
            language=self.language,
            beam_size=1,                      # greedy = fastest for short clips
            condition_on_previous_text=False,
            vad_filter=False,                 # we already trim silence ourselves
            temperature=0.0,
        )
        return "".join(seg.text for seg in segments)


def _model_cache_dir():
    from ..paths import models_dir

    return models_dir()


def available() -> bool:
    try:
        import faster_whisper  # noqa: F401
    except Exception:
        return False
    return True
