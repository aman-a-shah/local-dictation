# Changelog

All notable changes to **Local Dictation** are documented here. This project
adheres to [Semantic Versioning](https://semver.org/).

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

[1.0.0]: https://github.com/aman-a-shah/local-transcription/releases/tag/v1.0.0
