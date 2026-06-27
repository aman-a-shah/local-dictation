# Privacy Policy

**Effective date: 2026-06-18**

Voca is built on one promise: **your voice never leaves your
device.** This policy explains, in plain language, exactly what the app does
with your data — and, just as importantly, what it does *not* do.

The short version:

- Your audio is transcribed **entirely on your own computer**. It is never
  uploaded, streamed, or sent anywhere.
- There is **no account, no sign-in, and no telemetry** turned on by default.
- The **only** thing the app ever sends over the network is an optional check
  for a newer version, which transmits three non-identifying values: the app
  version, your operating system name, and your CPU architecture. Nothing else.
  You can turn this off.
- There are **no trackers, no analytics, no advertising, and no third-party
  data sharing** of any kind.

Everything below is detail in support of those four points.

---

## 1. Audio you speak

When you hold the push-to-talk key and speak, the app records audio from your
microphone into memory and runs it through a speech-recognition model
(Whisper) that lives **on your device**:

- On Apple Silicon Macs, transcription runs locally on the GPU via Apple's MLX
  framework.
- On Intel Macs and Windows, transcription runs locally on the CPU via
  faster-whisper (CTranslate2).

The audio is held only in memory for the moment it takes to transcribe, then
**discarded**. It is never written to a file, never saved to disk, and never
transmitted off the device. There is no cloud speech service involved at any
point. The app works fully offline, with your network disconnected.

## 2. What is stored locally (and only locally)

To power the in-app dashboard (recent transcriptions, total words, "time
saved," activity streaks), the app keeps a small **local history** of your
transcriptions in a SQLite database on your own machine. Each entry contains:

- the transcribed **text**,
- a **timestamp**,
- derived numbers: word count, character count, audio duration, and how long
  transcription took,
- the model name and language used.

This database is stored in your operating system's standard app-data folder:

- **macOS:** `~/Library/Application Support/Voca`
- **Windows:** `%APPDATA%\Voca`
- **Linux:** `~/.local/share/Voca`

This history **never leaves your device.** It is not synced, backed up by us,
or transmitted anywhere. It exists purely so the dashboard can show you your
own activity.

**You are in control of it:**

- **Disable it entirely** by setting the environment variable
  `DICTATE_HISTORY=0` — nothing will be recorded.
- **Clear it** at any time from the dashboard, or by deleting the database file
  in the folder above.

The app also writes ordinary diagnostic **log files** (for example
`~/Library/Logs/Voca.log` on macOS) to help you troubleshoot. These
stay on your device and are not sent anywhere.

## 3. What leaves your device

The app makes network requests in **exactly one** situation: the optional
**auto-update check**. When it runs (on launch, and when you press "Check for
updates" in the dashboard), it contacts the project's own update endpoint and
sends only these three values:

| Field | Example | Why |
|---|---|---|
| App version | `1.2.0` | To know whether a newer build exists |
| Operating system | `mac` / `windows` | To return the right download |
| CPU architecture | `arm64` / `x64` | To return the right build for your chip |

That is the complete list. The update check does **not** send:

- any audio or transcription,
- any of your local history,
- your name, email, IP-derived identity, or any account data,
- any unique device identifier, cookie, or persistent ID,
- anything else at all.

The response simply tells the app whether a newer version is available and,
if so, where to download it. You confirm any download and install yourself.

**You can disable the update check completely** by setting
`DICTATE_NO_UPDATE_CHECK=1`. With it disabled, the app makes no network
requests whatsoever during normal use.

> Note: like any network request, the update check necessarily reveals your IP
> address to the server that receives it — this is true of every internet
> connection and is unavoidable for a request to happen at all. We do not use
> it to identify or track you, and you can avoid even this by disabling the
> check.

## 4. No tracking, analytics, ads, or data sharing

Voca contains **no** analytics SDKs, **no** crash-reporting
services, **no** advertising, and **no** third-party tracking of any kind. We
do not build profiles, we do not sell or share data (there is no data to sell),
and there are no third parties receiving your information.

## 5. Children's privacy

Voca is a general-purpose utility and is not directed at children.
Because the app collects no personal information and requires no account, it
does not knowingly collect data from children or anyone else. If you believe a
child has somehow provided personal information through the app, please contact
us (below) — though in normal operation there is no such data for us to hold.

## 6. Your control, summarized

| What | How |
|---|---|
| Stop all local history | `DICTATE_HISTORY=0` |
| Clear existing history | Dashboard "clear," or delete the database file |
| Stop all network activity | `DICTATE_NO_UPDATE_CHECK=1` |
| Point updates at your own server | `DICTATE_UPDATE_URL=https://your-host` |
| Run fully offline | Just do it — the app needs no network to work |

## 7. Changes to this policy

If we change how the app handles data, we will update this policy and revise the
effective date above. Material changes will be noted in the release notes for
the version that introduces them. Because the app is open source, you can always
inspect exactly what it does in the source code.

## 8. Contact

Questions about privacy? Open an issue at
**https://github.com/aman-a-shah/voca/issues**. For sensitive
reports, use the repository's private security advisory channel.
