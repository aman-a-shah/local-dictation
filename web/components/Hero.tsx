"use client";

import { useEffect, useState } from "react";
import { Waveform, Tag, Kbd } from "@voca/ui";
import type { WaveMode } from "@voca/ui";
import { DownloadCTA } from "./DownloadCTA";
import { Tilt } from "./Tilt";
import styles from "./Hero.module.css";

const SAMPLE =
  "Let's ship the cross-platform build this week and write the release notes.";

function useDemo() {
  const [mode, setMode] = useState<WaveMode>("idle");
  const [typed, setTyped] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      setMode("idle");
      setTyped(SAMPLE);
      setDone(true);
      return;
    }
    const timers: ReturnType<typeof setTimeout>[] = [];
    let cancelled = false;
    const push = (fn: () => void, ms: number) => timers.push(setTimeout(fn, ms));

    function cycle() {
      if (cancelled) return;
      setTyped("");
      setDone(false);
      setMode("listening");
      const words = SAMPLE.split(" ");
      words.forEach((_, i) =>
        push(() => setTyped(words.slice(0, i + 1).join(" ")), 280 + i * 150)
      );
      const speakDone = 280 + words.length * 150;
      push(() => setMode("thinking"), speakDone + 150);
      push(() => {
        setMode("done");
        setDone(true);
      }, speakDone + 850);
      push(() => setMode("idle"), speakDone + 2600);
      push(cycle, speakDone + 4200);
    }
    push(cycle, 600);
    return () => {
      cancelled = true;
      timers.forEach(clearTimeout);
    };
  }, []);

  return { mode, typed, done };
}

const CHIPS = ["100% on-device", "No account", "No telemetry", "Open source"];

export function Hero() {
  const { mode, typed, done } = useDemo();

  return (
    <section className={`${styles.hero} ld-grain`}>
      <div className={styles.gridLines} aria-hidden="true" />
      <div className={`container ${styles.grid}`}>
        <div className={styles.copy}>
          <div className={styles.topRow}>
            <Tag>v1.0 · macOS &amp; Windows</Tag>
            <span className={styles.freeBadge}>
              <span className={styles.freePrice}>$0</span>
              Completely free, forever — no subscription
            </span>
          </div>
          <h1 className={styles.title}>
            Talk. It types.
            <br />
            Nothing leaves your{" "}
            <span className={styles.titleAccent}>
              Mac or PC
              <svg className={styles.underline} viewBox="0 0 220 12" preserveAspectRatio="none" aria-hidden="true">
                <path d="M2 8C40 3 110 2 218 6" fill="none" stroke="url(#hg)" strokeWidth="3" strokeLinecap="round" />
                <defs>
                  <linearGradient id="hg" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0" stopColor="#e9cf8f" />
                    <stop offset="0.5" stopColor="#d4af37" />
                    <stop offset="1" stopColor="#a9842a" />
                  </linearGradient>
                </defs>
              </svg>
            </span>
            .
          </h1>
          <p className={`lead ${styles.lead}`}>
            Hold a key, speak, release — your words are transcribed locally and
            pasted right at your cursor, in any app. No account, no network, no
            audio ever sent anywhere.
          </p>

          <div className={styles.chips}>
            {CHIPS.map((c) => (
              <span key={c} className={styles.chip}>
                <Check /> {c}
              </span>
            ))}
          </div>

          <div className={styles.actions}>
            <DownloadCTA />
          </div>

          <p className={styles.hint}>
            Hold <Kbd>fn</Kbd> on Mac · <Kbd>Left&nbsp;Ctrl</Kbd> on Windows. Free
            &amp; open source.
          </p>
        </div>

        <Tilt className={styles.demoTilt}>
          <div className={`${styles.demo} ld-on-dark`}>
            <div className={styles.demoChrome}>
              <span className={styles.dot} />
              <span className={styles.dot} />
              <span className={styles.dot} />
              <span className={styles.demoTitle}>Cursor — untitled</span>
            </div>
            <div className={styles.demoBody}>
              <p className={styles.transcript}>
                {typed}
                {!done && <span className={styles.caret} />}
              </p>
              <div className={styles.wave}>
                <Waveform mode={mode} height={96} bars={42} intensity={1.05} />
              </div>
              <div className={styles.statusRow}>
                <span
                  className={`${styles.status} ${
                    mode === "listening"
                      ? styles.statusLive
                      : done
                      ? styles.statusDone
                      : ""
                  }`}
                >
                  {mode === "listening"
                    ? "● Listening"
                    : mode === "thinking"
                    ? "Transcribing…"
                    : done
                    ? "✓ Inserted at cursor"
                    : "Hold to talk"}
                </span>
                <span className={styles.statusMeta}>on-device · 0 ms uploaded</span>
              </div>
            </div>
          </div>
        </Tilt>
      </div>
    </section>
  );
}

function Check() {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true" className={styles.chipCheck}>
      <path d="M3.5 8.5l3 3 6-7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
