# Changelog

All notable changes to **Local Dictation** are documented here. This project
adheres to [Semantic Versioning](https://semver.org/).

## [1.0.1] - 2026-06-22

### Fixed

- Waveform overlay now appears reliably every time you dictate. It could
  intermittently stay invisible — most often on the first dictation after a
  pause — even though transcription worked. The synchronous paint in `show()`
  only *marked* the panel for display; the pixels reached the screen at the main
  run loop's next Core Animation commit, which a GIL-heavy worker (the
  warm-on-press model re-warm, fired after 30s idle) could delay for the whole
  hold. The view is now layer-backed and the overlay commits + flushes its own
  Core Animation transaction in `show()` and per frame in `tick_`, pushing the
  bar to the screen before the main thread is yielded — so it shows (and
  animates) under any contention.

## [1.0.0] - 2026-06-18

### Added

- Cross-platform distributable packaging:
  - macOS `.dmg` for Apple Silicon and Intel (PyInstaller `.app` bundle,
    menu-bar agent, microphone usage description, UTF-8 environment).
  - Windows installer (`LocalDictationSetup-<version>.exe`) via Inno Setup, with
    Start Menu shortcut, optional desktop icon, and optional run-at-login.
- GitHub Actions release workflow (`v*` tag → build, `--selftest` smoke test,
  package, publish a Release with stable-named assets for the download site).
- Optional, secret-gated code signing + notarization (macOS) and Authenticode
  signing (Windows); builds run unsigned when secrets are absent.

[1.0.1]: https://github.com/aman-a-shah/local-dictation/releases/tag/v1.0.1
[1.0.0]: https://github.com/aman-a-shah/local-transcription/releases/tag/v1.0.0
