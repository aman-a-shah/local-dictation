# Design

## Theme

**"Warm voice, cold machine."** A deep near-black canvas — the app's native
habitat is the menu bar and the camera notch, and the brand promise is on-device
privacy, so the surface is dark, quiet, and precise like audio hardware. The one
warm thing is the voice: a rose/coral waveform that glows against the dark. A
cool cyan appears only while *listening*, like the live LED on a recording
interface. The reference lane is **precision audio instrument meets Linear-dark**,
explicitly NOT SaaS-cream, NOT purple-AI-gradient, NOT editorial-magazine.

Mode is dark by deliberate choice (scene: a developer dictating into their editor
at night, watching a thin waveform glow under the notch). The website and the
in-app dashboard share these exact tokens so opening the app feels like stepping
inside the site.

## Color (OKLCH)

Strategy: **Committed dark.** The dark surface carries the mood; rose is the brand
signal, cyan the live accent. Neutrals are tinted faintly cool (toward the canvas
hue), never warm.

| Role | Token | Value |
|---|---|---|
| Canvas (base bg) | `--bg` | `oklch(0.165 0.012 280)` |
| Surface (raised) | `--surface` | `oklch(0.205 0.013 282)` |
| Surface 2 (cards) | `--surface-2` | `oklch(0.245 0.015 283)` |
| Hairline | `--line` | `oklch(1 0 0 / 0.09)` |
| Hairline strong | `--line-strong` | `oklch(1 0 0 / 0.16)` |
| Ink (primary text) | `--ink` | `oklch(0.97 0.004 280)` |
| Muted (secondary) | `--muted` | `oklch(0.76 0.018 285)` |
| Faint (tertiary, large only) | `--faint` | `oklch(0.6 0.02 285)` |
| Brand / voice (primary) | `--rose` | `oklch(0.7 0.2 18)` |
| Brand bright (hover) | `--rose-bright` | `oklch(0.76 0.2 20)` |
| Live / listening accent | `--cyan` | `oklch(0.82 0.13 205)` |
| Success (inserted ✓) | `--mint` | `oklch(0.84 0.15 162)` |

Contrast: ink (L .97) and muted (L .76) both clear 4.5:1 on `--bg` (L .165). Rose
and cyan are used for large text, icons, and graphics only — never small body
copy. State is never color-only (always paired with a glyph/label).

## Typography

Self-hosted via @fontsource (no third-party font CDN — the privacy principle).
Contrast axis is **grotesque + monospace**, not two sans.

- **Display / UI sans:** `Schibsted Grotesk` — a precise grotesque with quiet
  personality; one family across weights 400/500/600/700. (Deliberately not
  Inter / Space Grotesk / DM Sans — reflex picks.)
- **Mono:** `JetBrains Mono` — earned (this is a real developer tool). Used for
  keycaps, stat numerals (tabular), model names, code, and the technical labels
  that would otherwise become tracked-uppercase eyebrows.
- Scale: fluid `clamp()`, ratio ≥1.25. Hero display max ≤ 6rem. Letter-spacing
  ≥ -0.03em on display. Dark-mode body line-height +0.07. Body measure 65–72ch.
  `text-wrap: balance` on h1–h3, `pretty` on prose.

## Components

- **Buttons:** solid rose primary (dark ink text for contrast), ghost/outline
  secondary on hairlines. Radius 10px. No pill-everything.
- **Keycap (`<kbd>`):** mono, raised surface, bottom hairline shadow — renders the
  push-to-talk key (fn / Left Ctrl) as a real key.
- **Waveform:** the hero object — animated rose bars on canvas; cyan while
  "listening". Canvas/SVG, reduced-motion → static bars.
- **Stat:** big tabular-mono numeral + sans label. NOT the SaaS hero-metric card
  template — laid into prose/asymmetric layout, not a 3-up card row.
- **Download chooser:** auto-detects OS/arch, shows the matched build prominently
  with the others one expand away.
- Cards used sparingly and only where they're the right affordance; never nested.

## Layout

- Max content width ~1200px; generous, varied vertical rhythm via `clamp()`.
- Asymmetric hero (copy + live waveform), not centered-everything.
- Responsive grids: `repeat(auto-fit, minmax(280px, 1fr))` where grids are right.
- Semantic z-index scale (dropdown < sticky < modal-backdrop < modal < toast).

## Motion

- One orchestrated hero load (waveform draws in, copy rises) + restrained,
  content-fitted reveals — not a uniform fade-on-scroll on every section.
- Ease-out (expo/quart). No bounce. Waveform is a continuous rAF loop.
- Full `prefers-reduced-motion` path: static waveform, instant/crossfade reveals,
  content always visible by default (never gated on a transition).
