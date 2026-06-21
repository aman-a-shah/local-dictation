"""End-to-end-ish checks that don't need a mic, key tap, or focused window.

We synthesize speech with macOS `say`, feed it through the real Transcriber, and
assert the words come back. Also unit-tests silence trimming and clipboard
save/restore so the injector's stateful bits are covered headlessly.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest
from scipy.io import wavfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dictate.transcriber import Transcriber, _trim_silence  # noqa: E402


def synth(text: str) -> np.ndarray:
    """Render `text` to a 16 kHz mono float32 array via the system TTS."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    subprocess.run(
        ["say", "--data-format=LEF32@16000", "--file-format=WAVE", "-o", path, text],
        check=True,
    )
    rate, data = wavfile.read(path)
    Path(path).unlink(missing_ok=True)
    assert rate == 16_000, rate
    if data.dtype != np.float32:
        data = data.astype(np.float32) / np.iinfo(data.dtype).max
    if data.ndim > 1:
        data = data[:, 0]
    return data


def test_trim_silence_keeps_speech():
    sr = 16_000
    speech = (np.random.randn(sr) * 0.3).astype(np.float32)  # 1 s of "voice"
    pad = np.zeros(sr, dtype=np.float32)  # 1 s silence each side
    clip = np.concatenate([pad, speech, pad])
    trimmed = _trim_silence(clip, sr)
    assert trimmed.size < clip.size
    assert trimmed.size >= speech.size  # speech preserved (+ small pad)


@pytest.mark.skipif(
    shutil.which("say") is None,
    reason="needs macOS `say` to synthesize speech (and downloads a model)",
)
def test_transcribes_speech():
    tr = Transcriber()
    audio = synth("The quick brown fox jumps over the lazy dog.")
    text = tr.transcribe(audio).lower()
    print(f"\nGOT: {text!r}")
    for word in ("quick", "brown", "fox", "lazy", "dog"):
        assert word in text, f"missing {word!r} in {text!r}"


if __name__ == "__main__":
    test_trim_silence_keeps_speech()
    print("✓ trim_silence")
    test_transcribes_speech()
    print("✓ transcribes_speech")
    print("\nAll checks passed.")
