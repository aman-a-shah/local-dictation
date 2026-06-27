# Changelog

All notable changes to **Voca** are documented here. This project
adheres to [Semantic Versioning](https://semver.org/).

## [1.0.2] - 2026-06-25

### Fixed

- The app can no longer freeze permanently or refuse to quit. Both symptoms had
  one root cause: each stage of the pipeline (mic capture, transcription, paste)
  runs on its own single-worker lane, and a task wedged in a native call that
  never returns — a ⌘V into a hung window server, a CoreAudio stream open caught
  in a device-change race — jammed every later task in that lane forever ("it
  just stops working"). Quit then hung too, because teardown waited *unbounded*
  on those same workers on the main thread, so a wedged worker froze the menu and
  the app could neither quit nor restart.
  - **Self-healing lanes:** a watchdog now rebuilds any lane whose in-flight task
    has run past a deadline it could only reach by hanging, abandoning the wedged
    worker (a leaked daemon thread) so dictation recovers on its own within a
    couple of seconds instead of needing a restart.
  - **Guaranteed quit:** the termination path arms a hard "deadman" that
    force-exits via `os._exit` after a short grace no matter what is wedged, tears
    down with bounded waits, then exits — `os._exit` also skips the interpreter /
    native-thread teardown (and the `concurrent.futures` atexit join of a wedged
    worker) that previously both crashed *and* hung the app on quit. Pressing Quit
    now always works, within a few seconds at most.
- Permission alerts now activate the app first, so an accessory-app dialog can't
  open unfocused/behind other windows while it blocks the main thread — which
  looked like a freeze with no visible prompt to dismiss.
- The waveform overlay now floats above the app you're actually using, on every
  Space, instead of sometimes hiding behind the active app and only being
  visible once you switched to the desktop. The bar still drew reliably (1.0.1);
  the problem was *where* it layered. Its collection behavior mixed
  `CanJoinAllSpaces` ("appear on every Space") with `Stationary` ("pin to the
  desktop; don't participate in Spaces") — contradictory flags the window server
  resolved by treating the bar as a desktop-attached element, stranding it on
  the desktop layer of one Space. `Stationary` is dropped; the panel keeps
  `CanJoinAllSpaces | FullScreenAuxiliary` so it rides above every app and
  follows you into full-screen Spaces, and that floating level + behavior is now
  re-asserted on every show so it can't get stranded again.

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
  - Windows installer (`VocaSetup-<version>.exe`) via Inno Setup, with
    Start Menu shortcut, optional desktop icon, and optional run-at-login.
- GitHub Actions release workflow (`v*` tag → build, `--selftest` smoke test,
  package, publish a Release with stable-named assets for the download site).
- Optional, secret-gated code signing + notarization (macOS) and Authenticode
  signing (Windows); builds run unsigned when secrets are absent.

[1.0.2]: https://github.com/aman-a-shah/voca/releases/tag/v1.0.2
[1.0.1]: https://github.com/aman-a-shah/voca/releases/tag/v1.0.1
[1.0.0]: https://github.com/aman-a-shah/voca/releases/tag/v1.0.0
