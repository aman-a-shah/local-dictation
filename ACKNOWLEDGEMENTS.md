# Acknowledgements

Local Dictation stands on a lot of excellent open-source work. This file credits
the third-party software the app depends on, grouped by role, with each
component's license. We are grateful to all of these projects and their
maintainers.

If you redistribute Local Dictation, note that these components are governed by
**their own licenses** (linked below), not by Local Dictation's MIT license.

## Transcription engines and models

| Component | Role | License |
|---|---|---|
| **OpenAI Whisper** | The speech-recognition model architecture and weights that power all transcription | MIT |
| **mlx-whisper** (Apple MLX) | Runs Whisper on Apple Silicon GPUs (the default engine on Apple Silicon Macs) | MIT |
| **faster-whisper** (built on **CTranslate2**) | Runs Whisper on CPU/CUDA via CTranslate2 (the engine on Windows and Intel Macs) | MIT |

The Whisper **model weights** are published by OpenAI under the MIT license.
On Apple Silicon, the app uses MLX-format conversions of these models
distributed by the `mlx-community` project on the Hugging Face Hub. Models are
downloaded once at first run and cached locally on your device.

## Audio capture

| Component | Role | License |
|---|---|---|
| **sounddevice** | Python bindings for microphone capture | MIT |
| **PortAudio** | The cross-platform native audio I/O library that sounddevice wraps | MIT-style (PortAudio license) |
| **NumPy** | Numerical array handling for audio buffers | BSD 3-Clause |
| **SciPy** | Signal-processing helpers (e.g. resampling/filtering) | BSD 3-Clause |

## User interface

| Component | Role | License |
|---|---|---|
| **pywebview** | Hosts the in-app dashboard in a native webview | BSD 3-Clause |
| **pyperclip** | Cross-platform clipboard access used for paste-based text injection | BSD 3-Clause |
| **pystray** | System-tray / menu-bar icon on Windows | **LGPL-3.0 / GPL-2.0 (dual-licensed)** — see note below |
| **Pillow (PIL Fork)** | Renders the tray/menu-bar icon images | HPND (MIT-CMU style, permissive) |

## Platform and input

| Component | Role | License |
|---|---|---|
| **pynput** | Global keyboard hook for the push-to-talk key (Windows / Intel paths) | **LGPL-3.0** — see note below |
| **pyobjc** (Quartz, Cocoa, AVFoundation, ApplicationServices) | Native macOS frameworks: the `fn`/globe key tap, the menu-bar app, microphone permission, and keystroke synthesis | MIT |
| **pywin32** | Windows API access used by the Windows build | PSF (Python Software Foundation) license |
| **platformdirs** | Resolves the correct per-OS locations for app data, logs, and the model cache | MIT |

## Packaging

| Component | Role | License |
|---|---|---|
| **PyInstaller** / **py2app** | Bundle the Python app into a distributable desktop application | See note below |

---

## License notes

**pynput (LGPL-3.0) and pystray (LGPL-3.0 / GPL-2.0).** These two libraries are
copyleft. Local Dictation uses them as unmodified, dynamically-loaded libraries
and does not incorporate their source into its own code. Under the LGPL, this
keeps Local Dictation's own MIT-licensed code separate while honoring the
libraries' terms. If you redistribute a build that includes them, you must
comply with the LGPL/GPL — in particular, preserving their license texts and
making their source (and any modifications you make to them) available. pystray
is dual-licensed; you may rely on the LGPL-3.0 option. We have not modified
either library.

**PyInstaller.** PyInstaller is licensed GPL-2.0-or-later **with a special
runtime/bootloader exception** that explicitly permits using it to package and
distribute applications under any license of your choosing — including
proprietary or MIT-licensed apps. Bundling Local Dictation with PyInstaller
therefore does **not** impose the GPL on Local Dictation itself. PyInstaller's
own source and license remain available from its project.

**py2app** (used for the macOS app bundle) is MIT-licensed.

---

## A note on accuracy

License identifiers above reflect each project's stated license at the time of
writing and the pinned versions in `requirements-base.txt`,
`requirements.txt`, `requirements-windows.txt`, and
`requirements-macos-intel.txt`. Licenses can change between versions; the
authoritative license for any component is the one shipped with the version you
are using. If you spot an error or omission here, please let us know at
**[your-contact-email]**.
