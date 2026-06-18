# Product

## Register

brand
<!-- The download website is the primary surface this register governs. The
in-app dashboard is a product surface that deliberately reuses this brand system
so the two feel like one product. -->

## Users

People who talk faster than they type and care where their words go: developers,
writers, researchers, founders, and anyone with RSI or accessibility needs. Their
context is mid-flow in another app — an editor, a doc, a chat — wanting to drop
spoken text at the cursor without breaking concentration or trusting a cloud
service with their voice. Many chose this specifically *because* it's local.

## Product Purpose

Local Dictation is push-to-talk voice typing that runs 100% on-device. Hold a key,
speak, release — your words are transcribed locally (Apple MLX on Apple Silicon,
faster-whisper elsewhere) and pasted wherever your cursor is. No cloud, no account,
no audio ever leaving the machine. The website's job is to make that promise
*felt* — fast, private, precise — and get the right build into the visitor's hands
in one click. Success = a visitor understands "my voice never leaves this device,"
trusts it, and downloads the correct build for their machine without thinking.

## Brand Personality

Private, precise, quietly fast. Voice: confident and plain-spoken, never hypey —
it states what the tool does and proves it. Three words: **calm, exact,
on-device.** The emotional goal is *trust through restraint*: the design should
feel like a well-made instrument (an audio interface, a mechanical keyboard), not
a SaaS funnel. A warm human signal (the voice) living inside a cool, dark,
precise machine.

## Anti-references

- Generic SaaS landing pages: cream/parchment backgrounds, a tracked-uppercase
  eyebrow over every section, identical 3-up icon-card grids, "hero metric"
  templates.
- The AI-product cliché: purple→blue gradient hero, gradient text, glassmorphism
  everywhere, "Powered by AI ✨" energy.
- Anything that looks like it wants your credit card or your data. No fake
  urgency, no cookie-wall vibes. The product's whole point is privacy; the site
  must embody it.

## Design Principles

1. **Practice the promise.** The site is as private and lightweight as the app —
   no trackers, no third-party fonts phoning home, fast and static.
2. **Show the signal.** A live waveform is the brand's hero object; voice is warm
   and visible, the machine around it is dark and quiet.
3. **One honest click.** Detect the visitor's OS/arch and offer the exact build,
   with every other build one expand away. Never make them guess.
4. **Instrument, not funnel.** Precision over persuasion: real numbers, real
   keys, monospace where it earns it, restraint everywhere else.
5. **The app and the site are one object.** The dashboard reuses these exact
   tokens so launching the app feels like stepping inside the website.

## Accessibility & Inclusion

Target WCAG 2.1 AA. Body text ≥ 4.5:1 on the dark canvas; never rely on the rose
or cyan accent alone to convey state (pair with text/icon). Full
`prefers-reduced-motion` alternative for the waveform and all reveals (the
audience explicitly includes people with motion sensitivity and RSI). Keyboard
operable throughout; visible focus rings.
