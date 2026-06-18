# Security Policy

We take the security of Local Dictation seriously. Because the app handles your
microphone and injects keystrokes on your behalf, we want any vulnerabilities
found and fixed responsibly.

## Reporting a vulnerability

**Please do not open a public issue for security vulnerabilities.**

Instead, report them privately to **[your-security-email]**. If you prefer
GitHub's private channel, you can also use the repository's
**Security → Report a vulnerability** (private advisory) feature at
**[your-repo-url]**.

When reporting, please include:

- a description of the issue and its potential impact,
- the version of Local Dictation and your OS/architecture,
- step-by-step reproduction instructions (and a proof of concept if you have
  one).

**Our commitment (responsible disclosure):**

- We will **acknowledge** your report within **3 business days**.
- We aim to provide an initial **assessment within 7 days**.
- We ask that you give us up to **90 days** to investigate and ship a fix
  before any public disclosure. We are happy to coordinate timing and to credit
  you in the release notes (unless you prefer to remain anonymous).

Please make a good-faith effort to avoid privacy violations, data destruction,
and service disruption while researching. We will not pursue or support legal
action against researchers who follow this policy.

## Supported versions

We provide security fixes for the **latest released version**. Older versions
are not maintained — if you are on an older build, please update.

| Version | Supported |
|---|---|
| Latest release | Yes |
| Older releases | No — please update |

## Important: current builds are unsigned

The current desktop builds are **not yet code-signed or notarized** on either
platform. This is a known, temporary state, and code signing is on the roadmap.
Until then, the operating system will warn you when you first open the app:

- **macOS:** the first launch may be blocked by Gatekeeper. **Right-click (or
  Control-click) the app and choose "Open,"** then confirm. (Alternatively:
  System Settings → Privacy & Security → "Open Anyway.")
- **Windows:** SmartScreen may show "Windows protected your PC." Click
  **"More info" → "Run anyway."**

We plan to sign and notarize future releases so these prompts go away. Until
they do, only download the app from the official source and verify it (below).

## Verifying your download

To make sure your download is genuine and untampered, each release publishes
**checksums (SHA-256)** alongside the build artifacts. After downloading,
compute the checksum of your file and compare it to the published value:

- **macOS / Linux:**

  ```bash
  shasum -a 256 "Local Dictation.dmg"
  ```

- **Windows (PowerShell):**

  ```powershell
  Get-FileHash .\LocalDictation-Setup.exe -Algorithm SHA256
  ```

If the value does not match the one published with the release, **do not run
the file** — delete it and report it to us.

Only download Local Dictation from the official website **[your-domain]** or the
official releases page at **[your-repo-url]**.

## Scope

This policy covers the Local Dictation application and its official build/release
process. Vulnerabilities in third-party dependencies (see `ACKNOWLEDGEMENTS.md`)
should generally be reported upstream, but please let us know if one affects
Local Dictation so we can update.
