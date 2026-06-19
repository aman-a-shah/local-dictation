"""Heads-up dictation overlay — a slim bar that drops from the camera notch.

A borderless, click-through ``NSPanel`` pinned just under the camera island at
the top-center of the main display. While you hold ``fn`` it slides down into
view and a row of thin bars reacts to your voice in real time; on release it
shows a calmer "thinking" shimmer during transcription, then slides back up
under the notch.

Everything here assumes it is driven on the **main thread**. The menu-bar
controller already marshals engine states onto the main thread (``drainStates_``)
before calling :meth:`Overlay.show` / :meth:`Overlay.set_mode` / :meth:`Overlay.hide`,
so those are safe. Live audio levels are read (not pushed) from a provider
callback inside the render tick, so PortAudio's callback thread never touches UI.

The whole thing is one 60 fps timer (:meth:`tick_`): it eases the panel's
position + opacity for the slide, and eases each bar's height toward a target
derived from the live mic level. No live audio during transcription, so that
phase synthesizes a gentle travelling pulse instead.
"""

from __future__ import annotations

import math
import time
from typing import Callable, Optional

import objc
from AppKit import (
    NSBackingStoreBuffered,
    NSBezierPath,
    NSColor,
    NSPanel,
    NSScreen,
    NSScreenSaverWindowLevel,
    NSView,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowCollectionBehaviorStationary,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
)
from Foundation import (
    NSMakeRect,
    NSObject,
    NSRunLoop,
    NSRunLoopCommonModes,
    NSTimer,
)

# -- Geometry (points) --------------------------------------------------------
# Everything scales off _SCALE, so resizing the whole bar is a one-line change.
_SCALE = 0.5
_BAR_W = 184.0 * _SCALE         # panel width
_BAR_H = 34.0 * _SCALE          # panel height
_PAD_X = 18.0 * _SCALE          # horizontal inset before first / after last stick
_N_BARS = 15                    # number of waveform sticks
_STICK_W = 3.0 * _SCALE         # thickness of each stick
_MIN_H = 3.0 * _SCALE           # resting (silent) stick height
_MAX_H = _BAR_H - 13.0 * _SCALE  # tallest a stick can grow

_GAP_UNDER_NOTCH = 6.0          # breathing room between the notch and the bar
_SLIDE = _BAR_H + _GAP_UNDER_NOTCH  # how far it travels on show/hide

# -- Reactivity tuning --------------------------------------------------------
# Two ideas work together so the bars react satisfyingly to ANY mic, quiet or
# loud, and adapt to your voice in real time:
#   1. An adaptive noise floor learns the ambient level and gates it out, so
#      steady background noise produces no motion — only talking does.
#   2. Automatic gain control (AGC): the gated signal is normalised against a
#      decaying envelope of its own recent peak, so a whisper and a shout both
#      fill the bars, and the response re-ranges as your volume changes. The old
#      design used a FIXED gain + absolute gate calibrated for a close mic, which
#      meant a quiet/far mic fell entirely below the gate and the bars never moved.
_NOISE_FALL = 0.5      # floor tracks *down* fast (re-learns a quieter room)
_NOISE_RISE = 0.01     # floor creeps *up* slowly, and only when you're not talking
_GATE_RATIO = 1.5      # raw must exceed the floor by this factor to count as voice
_ABS_GATE = 0.0004     # below this absolute RMS, treat as dead silence (no motion)
_PEAK_DECAY = 0.99     # AGC reference eases down (~halves in ~0.7 s at 60 fps)
_MIN_PEAK = 0.0008     # smallest AGC reference, so even a quiet voice fills the bars
_CURVE = 0.7           # <1 expands mid-levels so the bars pop instead of sitting low
_ATTACK = 0.6          # how fast a stick jumps up toward a louder target
_DECAY = 0.22          # how slowly it falls back (smoother than the rise)
_SCROLL_DT = 0.045     # seconds between history samples (waveform scroll speed)

# -- Colors (r, g, b, a) ------------------------------------------------------
_BG = (0.0, 0.0, 0.0, 0.82)              # near-black to blend with the notch
_LISTENING = (1.0, 1.0, 1.0, 0.95)       # bright white while hearing you
_THINKING = (0.62, 0.70, 1.0, 0.65)      # cool, dim shimmer while transcribing
_DONE = (0.30, 0.85, 0.45, 0.95)         # brief green confirmation


def _ease(cur: float, target: float, factor: float) -> float:
    return cur + (target - cur) * factor


class _WaveView(NSView):
    """Draws the pill background and the row of reacting sticks."""

    def initWithFrame_(self, frame):  # noqa: N802
        self = objc.super(_WaveView, self).initWithFrame_(frame)
        if self is None:
            return None
        self.levels = [0.0] * _N_BARS   # current animated stick heights, 0..1
        self.bar_rgba = _LISTENING
        return self

    def isOpaque(self):  # noqa: N802
        return False

    def drawRect_(self, _rect):  # noqa: N802
        bounds = self.bounds()
        w = bounds.size.width
        h = bounds.size.height

        # Background pill.
        radius = h / 2.0
        pill = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(bounds, radius, radius)
        NSColor.colorWithRed_green_blue_alpha_(*_BG).set()
        pill.fill()
        # Hairline rim so it reads as a discrete object on light wallpapers.
        NSColor.colorWithWhite_alpha_(1.0, 0.07).set()
        pill.setLineWidth_(1.0)
        pill.stroke()

        # Sticks, centered vertically, evenly spread across the inner width.
        n = len(self.levels)
        area = w - 2.0 * _PAD_X
        gap = (area - n * _STICK_W) / (n - 1) if n > 1 else 0.0
        cy = h / 2.0
        NSColor.colorWithRed_green_blue_alpha_(*self.bar_rgba).set()
        for i, v in enumerate(self.levels):
            bh = _MIN_H + (_MAX_H - _MIN_H) * v
            x = _PAD_X + i * (_STICK_W + gap)
            stick = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                NSMakeRect(x, cy - bh / 2.0, _STICK_W, bh),
                _STICK_W / 2.0,
                _STICK_W / 2.0,
            )
            stick.fill()


class Overlay(NSObject):
    """Owns the panel + render loop. Create and drive it on the main thread."""

    def initWithLevelProvider_(self, provider):  # noqa: N802
        self = objc.super(Overlay, self).init()
        if self is None:
            return None
        self._level_provider: Callable[[], float] = provider or (lambda: 0.0)
        self._panel: Optional[NSPanel] = None
        self._view: Optional[_WaveView] = None
        self._timer = None

        # Slide / fade state.
        self._cur_y = 0.0
        self._target_y = 0.0
        self._final_y = 0.0     # resting position, just under the notch
        self._hidden_y = 0.0    # tucked-up position, behind the notch
        self._x = 0.0
        self._alpha = 0.0
        self._target_alpha = 0.0
        self._visible = False

        self._mode = "listening"
        self._t0 = time.monotonic()
        # Recent loudness samples; bar i mirrors history[|i - center|], so the
        # newest sample spikes the center and ripples outward as you speak.
        self._history = [0.0] * (_N_BARS // 2 + 1)
        self._last_scroll = 0.0
        self._floor = 0.01      # adaptive ambient-noise estimate (settles fast)
        self._peak_env = 0.0    # AGC: decaying envelope of recent voice peak
        return self

    # -- construction --------------------------------------------------------
    @objc.python_method
    def build(self):
        rect = NSMakeRect(0.0, 0.0, _BAR_W, _BAR_H)
        panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            rect,
            NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel,
            NSBackingStoreBuffered,
            False,
        )
        panel.setOpaque_(False)
        panel.setBackgroundColor_(NSColor.clearColor())
        panel.setHasShadow_(True)
        panel.setLevel_(NSScreenSaverWindowLevel)  # float above menu bar / full-screen
        panel.setIgnoresMouseEvents_(True)         # clicks pass straight through
        panel.setReleasedWhenClosed_(False)
        panel.setHidesOnDeactivate_(False)
        panel.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorFullScreenAuxiliary
            | NSWindowCollectionBehaviorStationary
        )

        view = _WaveView.alloc().initWithFrame_(rect)
        panel.setContentView_(view)

        self._panel = panel
        self._view = view
        self._alpha = 0.0
        panel.setAlphaValue_(0.0)

    @objc.python_method
    def _pick_screen(self):
        """The screen the bar should drop from — the notched built-in if present.

        ``NSScreen.mainScreen()`` is "the screen with the key window", which for a
        windowless accessory app can be None or an external display, leaving the
        bar placed off-screen ("the overlay doesn't appear"). Prefer the screen
        that actually has a notch/menu-bar inset, then the primary screen, then
        mainScreen — and return None only if there are genuinely no screens.
        """
        screens = NSScreen.screens()
        if screens:
            for screen in screens:
                try:
                    if screen.safeAreaInsets().top > 0:
                        return screen  # the notched built-in display
                except AttributeError:
                    pass
            return screens[0]  # primary screen (owns the menu bar)
        return NSScreen.mainScreen()

    @objc.python_method
    def _recompute_geometry(self):
        """Place the bar centered under the notch on whatever screen is active.

        Leaves the previous geometry untouched if no screen is available, so a
        transient None (display asleep / mid-reconfiguration) can't park the bar
        at the origin where it would never be seen.
        """
        screen = self._pick_screen()
        if screen is None:
            return
        frame = screen.frame()
        vis = screen.visibleFrame()
        # Menu-bar gap; on notched Macs the safe-area top inset is taller.
        inset = frame.origin.y + frame.size.height - (vis.origin.y + vis.size.height)
        try:
            inset = max(inset, screen.safeAreaInsets().top)
        except AttributeError:
            pass  # pre-12.0 / no notch API

        top = frame.origin.y + frame.size.height - inset - _GAP_UNDER_NOTCH
        self._x = frame.origin.x + (frame.size.width - _BAR_W) / 2.0
        self._final_y = top - _BAR_H
        self._hidden_y = self._final_y + _SLIDE  # up behind the notch

    # -- public API (main thread) -------------------------------------------
    @objc.python_method
    def show(self):
        if self._panel is None:
            self.build()
        self._recompute_geometry()
        self._mode = "listening"
        self._history = [0.0] * len(self._history)  # start the waveform flat
        self._peak_env = 0.0  # re-range the AGC fresh for this utterance
        # Keep the learned ambient floor between takes (the room hasn't changed),
        # so the bars react from the very first syllable instead of sitting dead
        # while a re-primed floor settles.
        self._visible = True
        self._target_y = self._final_y
        self._target_alpha = 1.0
        # Begin tucked up behind the notch so it appears to emerge from under it.
        self._cur_y = self._hidden_y
        self._panel.setFrameOrigin_((self._x, self._cur_y))
        self._panel.orderFrontRegardless()
        self._start_timer()

    @objc.python_method
    def set_mode(self, mode: str):
        self._mode = mode

    @objc.python_method
    def hide(self):
        self._visible = False
        self._target_y = self._hidden_y
        self._target_alpha = 0.0
        self._start_timer()  # keep ticking so it animates out, then orders out

    # -- render loop ---------------------------------------------------------
    @objc.python_method
    def _start_timer(self):
        if self._timer is not None or self._panel is None:
            return
        # Add the timer in *common* modes so it keeps ticking even while the run
        # loop is in a tracking mode (e.g. the status-bar menu is open); a plain
        # scheduled timer only runs in the default mode and would freeze the
        # waveform mid-interaction.
        self._timer = NSTimer.timerWithTimeInterval_target_selector_userInfo_repeats_(
            1.0 / 60.0, self, "tick:", None, True
        )
        NSRunLoop.currentRunLoop().addTimer_forMode_(self._timer, NSRunLoopCommonModes)

    @objc.python_method
    def _stop_timer(self):
        if self._timer is not None:
            self._timer.invalidate()
            self._timer = None

    def tick_(self, _timer):  # noqa: N802 (runs on main thread)
        if self._panel is None:
            return

        # Slide + fade.
        self._cur_y = _ease(self._cur_y, self._target_y, 0.28)
        self._alpha = _ease(self._alpha, self._target_alpha, 0.28)
        self._panel.setFrameOrigin_((self._x, self._cur_y))
        self._panel.setAlphaValue_(max(0.0, min(1.0, self._alpha)))

        # Fully hidden -> order out and stop burning frames.
        if not self._visible and self._alpha < 0.02:
            self._panel.orderOut_(None)
            self._stop_timer()
            return

        self._render_bars()
        self._view.setNeedsDisplay_(True)

    @objc.python_method
    def _render_bars(self):
        t = time.monotonic() - self._t0
        view = self._view
        n = _N_BARS
        center = (n - 1) / 2.0

        if self._mode == "thinking":
            view.bar_rgba = _THINKING
            # No live audio while transcribing — synthesize a soft travelling wave.
            targets = [0.12 + 0.16 * (0.5 + 0.5 * math.sin(t * 4.0 - i * 0.55)) for i in range(n)]
        elif self._mode == "done":
            view.bar_rgba = _DONE
            targets = [_MIN_H / (_MAX_H - _MIN_H)] * n  # flatten to a calm line
        else:  # listening — drive the bars from the actual mic loudness
            view.bar_rgba = _LISTENING
            try:
                raw = float(self._level_provider())
            except Exception:
                raw = 0.0
            # Is this voice, or just the room? Voice is clearly above the floor.
            gate_on = raw > max(_ABS_GATE, self._floor * _GATE_RATIO)
            # Learn the ambient noise floor: drop toward it fast; let it creep up
            # only while you're NOT talking, so speech can't drag the gate up.
            if raw < self._floor:
                self._floor += (raw - self._floor) * _NOISE_FALL
            elif not gate_on:
                self._floor += (raw - self._floor) * _NOISE_RISE
            # The part of the signal above the ambient floor (0 when not voicing).
            signal = max(0.0, raw - self._floor) if gate_on else 0.0
            # AGC: snap the reference up to a new peak, ease it down otherwise, so
            # the bars auto-range to however loud you actually are right now.
            if signal > self._peak_env:
                self._peak_env = signal
            else:
                self._peak_env *= _PEAK_DECAY
            ref = max(self._peak_env, _MIN_PEAK)
            level = min(1.0, (signal / ref) ** _CURVE) if signal > 0.0 else 0.0

            # Scroll the loudness history outward from the center at a fixed rate
            # (independent of frame rate) so the waveform reads as *your* voice.
            if t - self._last_scroll >= _SCROLL_DT:
                self._last_scroll = t
                self._history.insert(0, level)
                self._history.pop()

            targets = [self._history[int(abs(i - center))] for i in range(n)]

        levels = view.levels
        for i, target in enumerate(targets):
            target = max(0.0, min(1.0, target))
            factor = _ATTACK if target > levels[i] else _DECAY
            levels[i] = _ease(levels[i], target, factor)

    # -- teardown ------------------------------------------------------------
    @objc.python_method
    def teardown(self):
        self._stop_timer()
        if self._panel is not None:
            self._panel.orderOut_(None)
