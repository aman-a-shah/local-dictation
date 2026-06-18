import type { Metadata } from "next";
import { Kbd } from "@local-dictation/ui";
import { REPO } from "@/lib/releases";
import styles from "./faq.module.css";

export const metadata: Metadata = {
  title: "FAQ",
  description: "Common questions about Local Dictation — privacy, accuracy, platforms, and setup.",
};

const FAQS: { q: string; a: React.ReactNode }[] = [
  {
    q: "Does my voice or text ever leave my device?",
    a: (
      <>
        No. Audio is transcribed locally by Whisper on your own CPU/GPU and then
        discarded. There’s no server. The only network request the app can make
        is an optional update check that sends just the app version and your OS —
        no audio, no transcripts, no identifiers. You can disable it.
      </>
    ),
  },
  {
    q: "How accurate is it, and how fast?",
    a: (
      <>
        It uses OpenAI’s Whisper models. On Apple Silicon it runs{" "}
        <code>large-v3-turbo</code> on the GPU (Apple MLX), typically 10–20×
        faster than real time. Intel Macs and Windows use faster-whisper on the
        CPU with a snappier default model; you can switch to a larger model for
        more accuracy in settings.
      </>
    ),
  },
  {
    q: "Which key do I hold to talk?",
    a: (
      <>
        <Kbd>fn</Kbd> (the globe key) on macOS, and <Kbd>Left&nbsp;Ctrl</Kbd> on
        Windows. macOS exposes <Kbd>fn</Kbd> as a real key; Windows doesn’t (it’s
        handled in keyboard firmware), so we default to Left Ctrl there. You can
        remap it in settings.
      </>
    ),
  },
  {
    q: "What languages are supported?",
    a: "Whisper handles 40+ languages and auto-detects by default. You can also pin a single language to skip detection and shave a little latency.",
  },
  {
    q: "Why does my OS warn me when I open it?",
    a: (
      <>
        The builds aren’t code-signed yet (signing certificates cost money for a
        free project). On macOS, right-click the app → <strong>Open</strong>. On
        Windows, choose <strong>More info → Run anyway</strong>. Signing is on the
        roadmap. You can verify the SHA-256 checksums published with each release.
      </>
    ),
  },
  {
    q: "Does it work in every app?",
    a: "Yes — it pastes at the system cursor, so it works anywhere you can type: editors, browsers, chat, email, terminals. Output is Unicode-safe (accents, emoji, CJK).",
  },
  {
    q: "What does it store, and where?",
    a: (
      <>
        A local SQLite history of your transcriptions (text, timestamps, word
        counts) powers the in-app dashboard. It lives in your OS app-data folder
        and never leaves the device. You can disable history or clear it anytime
        from the dashboard.
      </>
    ),
  },
  {
    q: "Is it really free?",
    a: (
      <>
        Yes — free and open source, no subscription, no account. The code is on{" "}
        <a href={`https://github.com/${REPO}`}>GitHub</a>.
      </>
    ),
  },
  {
    q: "How do I uninstall it?",
    a: "macOS: quit from the menu bar and move the app to the Trash. Windows: use Add/Remove Programs. To remove the model and history too, delete the LocalDictation folder in your app-data directory.",
  },
];

export default function FAQPage() {
  return (
    <div className="container container--narrow section">
      <header className={styles.head}>
        <h1 className={styles.h1}>Questions, answered.</h1>
        <p className="lead">
          Still stuck? Open an issue on{" "}
          <a className={styles.link} href={`https://github.com/${REPO}/issues`}>
            GitHub
          </a>
          .
        </p>
      </header>
      <div className={styles.list}>
        {FAQS.map((f, i) => (
          <details key={i} className={styles.item} open={i === 0}>
            <summary className={styles.summary}>{f.q}</summary>
            <div className={styles.answer}>{f.a}</div>
          </details>
        ))}
      </div>
    </div>
  );
}
