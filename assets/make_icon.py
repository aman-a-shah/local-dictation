#!/usr/bin/env python3
"""Generate the Local Dictation app icon: a white audio *waveform* on a violet
squircle, rendered in the macOS Big Sur style.

Why Quartz (CoreGraphics) and not Pillow: the app already depends on PyObjC, so
this adds no new dependency. We render each iconset size natively (crisper than
downscaling one master), then `iconutil` packs them into AppIcon.icns.

    python assets/make_icon.py        # -> assets/AppIcon.icns (+ AppIcon.iconset)

Editing the logo is cheap: the live bundle references this .icns by *symlink*,
so re-running this script updates the icon without touching the code signature.
Refresh the on-screen icon afterwards with:  touch the .app; killall Dock Finder
"""
from __future__ import annotations

import os
import subprocess
import sys

import Quartz
from CoreFoundation import CFURLCreateWithFileSystemPath, kCFURLPOSIXPathStyle

HERE = os.path.dirname(os.path.abspath(__file__))
ICONSET = os.path.join(HERE, "AppIcon.iconset")
ICNS = os.path.join(HERE, "AppIcon.icns")

# Background gradient (top -> bottom): black, with a whisper of lift at the top
# so the squircle still reads as a 3-D object rather than a flat hole.
TOP = (0.13, 0.13, 0.13, 1.0)   # #212121
BOTTOM = (0.0, 0.0, 0.0, 1.0)   # #000000

# Symmetric audio-waveform bar heights as a fraction of the usable height.
# Highest in the middle, tapering out — the classic "speaking" silhouette.
BARS = [0.45, 0.78, 1.0, 0.78, 0.45]

# Apple's icon grid: artwork sits inside a margin, not edge-to-edge.
SQUIRCLE_INSET = 0.098   # fraction of the canvas on each side
CORNER_RATIO = 0.2237    # corner radius / squircle side (Big Sur continuous-ish)


def _rounded_rect_path(x, y, w, h, radius):
    return Quartz.CGPathCreateWithRoundedRect(
        Quartz.CGRectMake(x, y, w, h), radius, radius, None
    )


def render(size: int, path: str) -> None:
    cs = Quartz.CGColorSpaceCreateDeviceRGB()
    ctx = Quartz.CGBitmapContextCreate(
        None, size, size, 8, 0, cs, Quartz.kCGImageAlphaPremultipliedLast
    )
    # Smooth edges.
    Quartz.CGContextSetAllowsAntialiasing(ctx, True)
    Quartz.CGContextSetShouldAntialias(ctx, True)
    Quartz.CGContextSetInterpolationQuality(ctx, Quartz.kCGInterpolationHigh)

    # --- Squircle background with vertical gradient -------------------------
    inset = size * SQUIRCLE_INSET
    side = size - 2 * inset
    radius = side * CORNER_RATIO
    squircle = _rounded_rect_path(inset, inset, side, side, radius)

    Quartz.CGContextSaveGState(ctx)
    Quartz.CGContextAddPath(ctx, squircle)
    Quartz.CGContextClip(ctx)
    gradient = Quartz.CGGradientCreateWithColorComponents(
        cs, [*BOTTOM, *TOP], [0.0, 1.0], 2  # comp order is bottom@0 -> top@1
    )
    Quartz.CGContextDrawLinearGradient(
        ctx,
        gradient,
        Quartz.CGPointMake(0, inset),         # bottom
        Quartz.CGPointMake(0, size - inset),  # top
        0,
    )
    Quartz.CGContextRestoreGState(ctx)

    # --- White waveform bars ------------------------------------------------
    n = len(BARS)
    # Bars span the central ~58% of the squircle width.
    span = side * 0.58
    bar_w = span / (n * 1.8)         # 1.8 -> bar:gap ratio
    gap = (span - n * bar_w) / (n - 1)
    max_h = side * 0.62              # tallest bar height
    cx = size / 2.0
    cy = size / 2.0
    start_x = cx - span / 2.0

    Quartz.CGContextSetRGBFillColor(ctx, 1.0, 1.0, 1.0, 1.0)
    for i, frac in enumerate(BARS):
        h = max_h * frac
        x = start_x + i * (bar_w + gap)
        y = cy - h / 2.0
        cap = bar_w / 2.0  # fully rounded bar ends
        Quartz.CGContextAddPath(ctx, _rounded_rect_path(x, y, bar_w, h, cap))
    Quartz.CGContextFillPath(ctx)

    # --- Export PNG ---------------------------------------------------------
    image = Quartz.CGBitmapContextCreateImage(ctx)
    url = CFURLCreateWithFileSystemPath(None, path, kCFURLPOSIXPathStyle, False)
    dest = Quartz.CGImageDestinationCreateWithURL(url, "public.png", 1, None)
    Quartz.CGImageDestinationAddImage(dest, image, None)
    if not Quartz.CGImageDestinationFinalize(dest):
        raise RuntimeError(f"failed to write {path}")


def main() -> int:
    os.makedirs(ICONSET, exist_ok=True)
    # (filename, pixel size) pairs iconutil expects.
    targets = [
        ("icon_16x16.png", 16),
        ("icon_16x16@2x.png", 32),
        ("icon_32x32.png", 32),
        ("icon_32x32@2x.png", 64),
        ("icon_128x128.png", 128),
        ("icon_128x128@2x.png", 256),
        ("icon_256x256.png", 256),
        ("icon_256x256@2x.png", 512),
        ("icon_512x512.png", 512),
        ("icon_512x512@2x.png", 1024),
    ]
    for name, px in targets:
        render(px, os.path.join(ICONSET, name))

    subprocess.run(
        ["iconutil", "-c", "icns", ICONSET, "-o", ICNS], check=True
    )
    print(f"wrote {ICNS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
