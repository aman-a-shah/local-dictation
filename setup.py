"""py2app build config for "Local Dictation.app".

Build with the helper script (recommended):

    ./build_app.sh

or directly in alias mode (references this project/venv in place — fast, not
relocatable, perfect for personal use):

    .venv/bin/python setup.py py2app -A

Alias mode matters: py2app places a real Python stub as the bundle's main
executable inside Contents/MacOS, so macOS attributes Microphone / Accessibility
permissions to *this app* rather than to the shared framework Python.app.
"""

from setuptools import setup

APP = ["run_menubar.py"]

OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "Local Dictation",
        "CFBundleDisplayName": "Local Dictation",
        "CFBundleIdentifier": "com.local.dictation",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1.0.0",
        # Menu-bar agent: no Dock icon, no window.
        "LSUIElement": True,
        "LSMinimumSystemVersion": "13.0",
        "NSMicrophoneUsageDescription": (
            "Local Dictation records audio while you hold the fn key so it can "
            "transcribe your speech on-device."
        ),
        "NSHighResolutionCapable": True,
        # LaunchServices starts apps with no locale, so Python defaults file I/O to
        # ASCII and chokes on any non-ASCII text (e.g. transcripts, the … glyph).
        # Force UTF-8 everywhere. These are read at interpreter startup, so they
        # must be set in the bundle environment, not at runtime.
        "LSEnvironment": {
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "LANG": "en_US.UTF-8",
            "LC_ALL": "en_US.UTF-8",
        },
    },
}

setup(
    name="Local Dictation",
    app=APP,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
