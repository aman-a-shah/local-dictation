# 🎙️ Local Dictation for macOS

Hold the **`fn` (🌐 globe) key**, speak, and release — your words are transcribed
**100% locally** and pasted at the cursor in whatever app you're in. No cloud, no
network, no API keys.

Built for Apple Silicon: transcription runs on the GPU via **MLX-Whisper**
(`large-v3-turbo`), typically **10–20× faster than real time**, so a few seconds
of speech lands almost instantly.

---

## Quick start

```bash
./dictate.sh
```

The first run creates a virtualenv, installs dependencies, and downloads the
Whisper model (~1.6 GB, cached afterwards). Then:

1. Grant the two permissions macOS asks for (see below).
2. Hold **`fn`**, speak, release. The text appears where your cursor is.
3. `Ctrl-C` in the terminal to quit.

You'll hear a soft **Tink** when it starts listening and a **Pop** when text is
inserted.

---

## Permissions (one-time)

macOS gates global key capture and synthetic keystrokes behind two permissions.
Grant them to the app you launch `dictate.sh` from (Terminal, iTerm, or your IDE):

| Permission | Where | Why |
|---|---|---|
| **Accessibility** | System Settings → Privacy & Security → **Accessibility** | Detect the `fn` key globally and paste text |
| **Microphone** | System Settings → Privacy & Security → **Microphone** | Record while you hold `fn` |

After adding Accessibility permission you may need to **quit and relaunch** the
terminal for it to take effect.

### Stop `fn` from opening the emoji picker

By default macOS may map the globe key to "Show Emoji & Symbols" or "Start
Dictation". For the cleanest experience set it to do nothing:

**System Settings → Keyboard → "Press 🌐 key to" → _Do Nothing_.**

(The engine works regardless — this just stops the OS from also reacting.)

---

## How it works

```
 fn down ──▶ mic stream starts (16 kHz mono, low-latency PortAudio)
 fn up   ──▶ buffer ──▶ trim silence ──▶ MLX-Whisper (GPU) ──▶ paste at cursor
```

Speed comes from a few deliberate choices, all in `dictate/`:

- **Warm model.** The model is loaded and a dummy inference is run at startup, so
  the first real take pays no compile/load tax. (`transcriber.py`)
- **Native-rate capture.** Audio is recorded at Whisper's own 16 kHz, mono, so
  there's no resampling step. (`audio.py`)
- **Silence trimming.** Leading/trailing dead air is gated out before inference,
  which is the single biggest lever on latency. (`transcriber.py`)
- **Off-thread pipeline.** The `fn`-key tap thread only starts/stops the mic;
  transcription and pasting happen on a worker so nothing blocks. (`app.py`)
- **Clipboard paste.** Insertion is a single ⌘V (instant, Unicode-safe) with your
  original clipboard restored a moment later. (`injector.py`)

---

## Configuration

Everything is tunable via `DICTATE_*` environment variables — no code edits:

| Variable | Default | Notes |
|---|---|---|
| `DICTATE_MODEL` | `mlx-community/whisper-large-v3-turbo` | Try `…/whisper-tiny` or `…/whisper-base` for max speed, `…/distil-whisper-large-v3` for a middle ground |
| `DICTATE_LANGUAGE` | `en` | Set `auto` to auto-detect (slightly slower) |
| `DICTATE_INJECT` | `paste` | `type` to emit keystrokes instead (for apps that block paste) |
| `DICTATE_APPEND_SPACE` | `1` | Add a trailing space after each insert |
| `DICTATE_RESTORE_CLIPBOARD` | `1` | Restore your clipboard after pasting |
| `DICTATE_SOUND` | `1` | Audio cues on/off |
| `DICTATE_MIN_SECONDS` | `0.30` | Ignore taps shorter than this |
| `DICTATE_MAX_SECONDS` | `120` | Safety cap on a single take |

Example — fastest possible, English, no sounds:

```bash
DICTATE_MODEL=mlx-community/whisper-base DICTATE_SOUND=0 ./dictate.sh
```

---

## Testing

```bash
.venv/bin/python tests/test_pipeline.py
```

This synthesizes speech with macOS `say`, runs it through the real model, and
asserts the words come back — no microphone or permissions needed.

---

## Troubleshooting

- **"Could not create event tap"** → Accessibility permission missing; grant it
  and relaunch the terminal.
- **Nothing is pasted** → check Accessibility (for ⌘V) and try
  `DICTATE_INJECT=type`.
- **No audio / empty results** → check Microphone permission and your input
  device in System Settings → Sound.
- **First run is slow** → it's downloading the model once; subsequent runs are
  fast.

## Requirements

- Apple Silicon Mac (M1 or newer)
- macOS 13+
- Python 3.10+
