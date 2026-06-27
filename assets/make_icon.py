#!/usr/bin/env python3
"""Generate the Voca app icon: the website brand mark (packages/ui
Logo.tsx) — a 4-bar audio *waveform* on a dark (#19191f) squircle — rendered in
the macOS Big Sur style. Same mark as the website, except the bars are WHITE
here instead of gold.

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

# Flat squircle background, matching the website brand mark's --ink-strong.
BG = (0.098, 0.098, 0.122, 1.0)   # #19191f

# Audio-waveform bars, identical to the website mark (packages/ui Logo.tsx):
# bar centers + heights on a 32-unit grid. The website renders them gold; the
# app renders them WHITE (the one intentional difference between the two marks).
WEB_GRID = 32.0
BAR_CENTERS = (8, 13, 18, 23)       # x of each bar's center on the 32-grid
BAR_HEIGHTS = (11, 6, 18, 9)        # height of each bar on the 32-grid
BAR_W = 2.8                          # bar width on the 32-grid (rx = BAR_W / 2)

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

    # --- Flat squircle background -------------------------------------------
    inset = size * SQUIRCLE_INSET
    side = size - 2 * inset
    radius = side * CORNER_RATIO
    squircle = _rounded_rect_path(inset, inset, side, side, radius)

    Quartz.CGContextAddPath(ctx, squircle)
    Quartz.CGContextSetRGBFillColor(ctx, *BG)
    Quartz.CGContextFillPath(ctx)

    # --- White waveform bars (same arrangement as the website mark) ---------
    # Map the website's 32-unit grid onto the squircle, which spans [inset, inset+side].
    scale = side / WEB_GRID
    bar_w = BAR_W * scale
    cap = bar_w / 2.0                # fully rounded bar ends (rx = width / 2)
    cy = size / 2.0                  # bars are centered vertically, like the website

    Quartz.CGContextSetRGBFillColor(ctx, 1.0, 1.0, 1.0, 1.0)
    for center_x, h32 in zip(BAR_CENTERS, BAR_HEIGHTS):
        h = h32 * scale
        x = inset + center_x * scale - bar_w / 2.0
        y = cy - h / 2.0
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
