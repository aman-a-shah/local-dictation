# Design

## Theme

**Light, premium, precise — "white instrument, warm voice."** A pure-white
canvas with deep ink, generous space, crisp hairlines, and soft shadows — the
Stripe / Linear-light / Apple lane of restraint. The one warm thing is the voice:
a single coral accent (the waveform, key CTAs). A cool blue appears only while
*listening*, like the live LED on a recording interface. **No gradients** — solid
fills, hairlines, and soft shadows only. Explicitly NOT SaaS-cream, NOT
purple-AI-gradient, NOT editorial-magazine.

Scene: a clean, bright workspace; the product feels like a well-made instrument,
not a funnel. The hero "editor" demo is a single dark panel for premium contrast
against the white page. The website and the in-app dashboard share these exact
tokens so opening the app feels like stepping inside the site.

## Color (OKLCH)

Strategy: **Restrained** — white canvas + tinted-cool neutrals + ONE coral accent
(≤10% of the surface). Neutrals are tinted faintly cool, never warm.

| Role | Token | Value |
|---|---|---|
| Canvas (base bg) | `--bg` | `oklch(1 0 0)` (pure white) |
| Soft band | `--bg-soft` | `oklch(0.985 0.003 265)` |
| Surface (cards) | `--surface` | `oklch(1 0 0)` + hairline + soft shadow |
| Dark panel (rare) | `--surface-ink` | `oklch(0.22 0.012 265)` (hero demo) |
| Hairline | `--line` | `oklch(0.27 0.011 265 / 0.1)` |
| Ink (headings) | `--ink-strong` | `oklch(0.19 0.012 265)` |
| Ink (body) | `--ink` | `oklch(0.27 0.011 265)` |
| Muted (secondary) | `--muted` | `oklch(0.47 0.012 265)` |
| Accent / voice | `--accent` | `oklch(0.6 0.2 22)` (coral) |
| Accent hover | `--accent-strong` | `oklch(0.53 0.21 22)` |
| Live / listening | `--live` | `oklch(0.55 0.13 235)` |
| Success (inserted ✓) | `--mint` | `oklch(0.58 0.13 162)` |

Contrast: ink (L .27) and muted (L .47) both clear 4.5:1 on white. Accent + live
are used for large text, icons, and graphics only — never small body copy. State
is never color-only (always paired with a glyph/label).

## Motion

Premium, restrained: Lenis inertial smooth scroll; staggered scroll-reveals
(content visible by default, motion only enhances); count-up on stats entering
view; a thin accent scroll-progress bar in the nav; hover underlines on links.
All ease-out (expo/quart), no bounce. Full `prefers-reduced-motion` path:
Lenis off, reveals instant, count-ups jump to final.

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
