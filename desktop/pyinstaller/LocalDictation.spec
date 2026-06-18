# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for "Local Dictation" — one spec, three targets.

This single spec drives the distributable builds on all supported platforms; it
branches on ``sys.platform`` / ``platform.machine()`` so the same file works for:

  * macOS Apple Silicon (arm64)  -> .app bundle, MLX (mlx-whisper) backend
  * macOS Intel       (x86_64)   -> .app bundle, faster-whisper backend
  * Windows           (x64)      -> onedir .exe, faster-whisper backend

Run from the repo root:

    pyinstaller --noconfirm --clean desktop/pyinstaller/LocalDictation.spec

Notes / pitfalls handled below:
  * faster_whisper + ctranslate2 need their bundled data + dynamic libs, and
    ctranslate2 has C-extension submodules PyInstaller misses -> collect_all.
  * sounddevice ships the PortAudio shared library as package data -> collect_all.
  * pywebview ('webview') ships JS/HTML assets + per-platform backends that it
    imports lazily -> collect_all.
  * mlx_whisper is Apple-Silicon ONLY; importing/collecting it on Intel or
    Windows would fail, so it is guarded behind a platform check.
  * The dashboard web build (dashboard/dist/**) is bundled under a top-level
    ``dashboard/`` folder, which dashboard_window.py resolves via sys._MEIPASS
    (onefile) or the executable dir (onedir / .app). Model weights are NOT
    bundled — they are downloaded on first run.
"""

import glob
import os
import platform
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules

# --------------------------------------------------------------------------- #
# Paths. SPECPATH is the dir containing this spec; the repo root is two up
# (desktop/pyinstaller/ -> desktop/ -> repo root).
# --------------------------------------------------------------------------- #
SPEC_DIR = os.path.abspath(SPECPATH)  # noqa: F821 (SPECPATH injected by PyInstaller)
REPO_ROOT = os.path.abspath(os.path.join(SPEC_DIR, os.pardir, os.pardir))

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform.startswith("win")
IS_MAC_ARM = IS_MAC and platform.machine() == "arm64"

APP_NAME = "Local Dictation"
BUNDLE_ID = "com.local.dictation"

# Read the version from dictate/__init__.py without importing the package
# (importing would pull in heavy native deps just to read a string).
def _read_version() -> str:
    init_path = os.path.join(REPO_ROOT, "dictate", "__init__.py")
    with open(init_path, "r", encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("__version__"):
                return line.split("=", 1)[1].strip().strip("\"'")
    return "0.0.0"


VERSION = _read_version()

# --------------------------------------------------------------------------- #
# Collect data files, binaries and hidden imports from third-party packages.
# collect_all returns (datas, binaries, hiddenimports) tuples.
# --------------------------------------------------------------------------- #
datas = []
binaries = []
hiddenimports = []


def _add(pkg_name):
    """collect_all a package, tolerating absence (logged, not fatal)."""
    try:
        d, b, h = collect_all(pkg_name)
        datas.extend(d)
        binaries.extend(b)
        hiddenimports.extend(h)
        print(f"[spec] collected {pkg_name}: {len(d)} datas, {len(b)} bins, {len(h)} imports")
    except Exception as exc:  # pragma: no cover - depends on install
        print(f"[spec] WARNING: could not collect {pkg_name}: {exc}")


# Transcription engine — faster-whisper everywhere; MLX on Apple Silicon only.
_add("faster_whisper")
_add("ctranslate2")
if IS_MAC_ARM:
    _add("mlx_whisper")
    _add("mlx")  # the mlx array library mlx_whisper depends on

# Audio I/O — bundles the PortAudio shared library.
_add("sounddevice")

# Numerics. numpy/scipy hooks ship with PyInstaller, but collect_all pulls the
# data files (e.g. scipy's compiled extensions) reliably across versions.
_add("scipy")
_add("numpy")

# Native webview window (dashboard). Ships JS/HTML + lazily-imported backends.
_add("webview")

# Misc pure/near-pure deps that are imported lazily or via plugin lookup.
hiddenimports += collect_submodules("platformdirs")
hiddenimports += ["pyperclip"]

# tokenizers / huggingface_hub are pulled in by faster_whisper at model load.
hiddenimports += collect_submodules("tokenizers")
try:
    _hf_d, _hf_b, _hf_h = collect_all("huggingface_hub")
    datas += _hf_d
    binaries += _hf_b
    hiddenimports += _hf_h
except Exception as exc:  # pragma: no cover
    print(f"[spec] WARNING: huggingface_hub not collected: {exc}")

# --------------------------------------------------------------------------- #
# Platform-specific hidden imports.
# --------------------------------------------------------------------------- #
if IS_MAC:
    # pyobjc frameworks used by the menu-bar app, overlay, mic permission and
    # text injection. PyInstaller's objc hook covers a lot, but the individual
    # framework wrappers are imported by name at runtime so list them explicitly.
    hiddenimports += [
        "objc",
        "Foundation",
        "AppKit",
        "Quartz",
        "AVFoundation",
        "ApplicationServices",
        "CoreFoundation",
        "PyObjCTools",
    ]
    hiddenimports += collect_submodules("Quartz")
    hiddenimports += collect_submodules("AppKit")
    hiddenimports += collect_submodules("AVFoundation")
    hiddenimports += collect_submodules("ApplicationServices")

if IS_WIN:
    # Tray app + global keyboard hook + clipboard/text injection on Windows.
    hiddenimports += [
        "pynput",
        "pynput.keyboard",
        "pynput.mouse",
        "pystray",
        "PIL",
        "PIL.Image",
        "win32api",
        "win32con",
        "win32gui",
        "win32clipboard",
        "win32process",
        "pywintypes",
    ]
    hiddenimports += collect_submodules("pynput")
    hiddenimports += collect_submodules("pystray")

# Always ensure the app's own submodules are seen even when imported lazily
# (factory.py imports both backends; main.py dispatches by platform).
hiddenimports += collect_submodules("dictate")

# --------------------------------------------------------------------------- #
# Bundle the built dashboard web assets under a top-level "dashboard/" folder.
# Guarded so a build before the web assets land just warns instead of failing.
# --------------------------------------------------------------------------- #
dashboard_dist = os.path.join(REPO_ROOT, "dashboard", "dist")
if os.path.isdir(dashboard_dist):
    n = 0
    for path in glob.glob(os.path.join(dashboard_dist, "**", "*"), recursive=True):
        if os.path.isfile(path):
            rel = os.path.relpath(os.path.dirname(path), dashboard_dist)
            dest = "dashboard" if rel == "." else os.path.join("dashboard", rel)
            datas.append((path, dest))
            n += 1
    print(f"[spec] bundled dashboard: {n} files from {dashboard_dist}")
else:
    print(
        f"[spec] WARNING: {dashboard_dist} not found — building WITHOUT the "
        "dashboard UI. Run `npm --prefix dashboard run build` first for a "
        "complete app."
    )

# --------------------------------------------------------------------------- #
# Icon resolution.
# --------------------------------------------------------------------------- #
ICNS_PATH = os.path.join(REPO_ROOT, "assets", "AppIcon.icns")
# The .ico is generated in CI from the PNGs (see .github/workflows/release.yml)
# and dropped next to this spec; fall back to None if it is missing locally.
ICO_PATH = os.path.join(SPEC_DIR, "AppIcon.ico")

mac_icon = ICNS_PATH if os.path.isfile(ICNS_PATH) else None
win_icon = ICO_PATH if os.path.isfile(ICO_PATH) else None

# --------------------------------------------------------------------------- #
# Analysis / build graph.
# --------------------------------------------------------------------------- #
ENTRY = os.path.join(REPO_ROOT, "run_app.py")

# Trim weight: never bundle the alternate backend's heavy native stack or test
# frameworks. (faster_whisper is always kept; mlx only on arm64 above.)
excludes = ["pytest", "tkinter"]
if not IS_MAC_ARM:
    excludes += ["mlx", "mlx_whisper"]

a = Analysis(
    [ENTRY],
    pathex=[REPO_ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

# --------------------------------------------------------------------------- #
# macOS: onedir EXE -> COLLECT -> .app BUNDLE.
# --------------------------------------------------------------------------- #
if IS_MAC:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=APP_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,  # GUI / agent app: no terminal window.
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,  # build native; the runner arch decides arm64 vs x86_64.
        codesign_identity=None,  # signing handled post-build in CI when secrets exist.
        entitlements_file=None,
        icon=mac_icon,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name=APP_NAME,
    )

    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        icon=mac_icon,
        bundle_identifier=BUNDLE_ID,
        version=VERSION,
        info_plist={
            "CFBundleName": APP_NAME,
            "CFBundleDisplayName": APP_NAME,
            "CFBundleIdentifier": BUNDLE_ID,
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            # Menu-bar agent: no Dock icon, no main window.
            "LSUIElement": True,
            "LSMinimumSystemVersion": "13.0",
            "NSHighResolutionCapable": True,
            "NSMicrophoneUsageDescription": (
                "Local Dictation records audio while you hold the fn key so it "
                "can transcribe your speech on-device."
            ),
            # LaunchServices starts apps with no locale; force UTF-8 so file I/O
            # on non-ASCII transcripts doesn't choke. Read at interpreter start,
            # so they must live in the bundle environment.
            "LSEnvironment": {
                "PYTHONUTF8": "1",
                "PYTHONIOENCODING": "utf-8",
                "LANG": "en_US.UTF-8",
                "LC_ALL": "en_US.UTF-8",
            },
        },
    )

# --------------------------------------------------------------------------- #
# Windows: onedir EXE + COLLECT (background tray app, no console).
# --------------------------------------------------------------------------- #
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=APP_NAME,  # produces "Local Dictation.exe"
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,  # windowed: background tray app, no console window.
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=win_icon,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name=APP_NAME,
    )
