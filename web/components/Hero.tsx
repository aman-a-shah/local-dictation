"use client";

import { useEffect, useState } from "react";
import { Waveform, Tag, Kbd } from "@local-dictation/ui";
import type { WaveMode } from "@local-dictation/ui";
import { DownloadCTA } from "./DownloadCTA";
import styles from "./Hero.module.css";

const SAMPLE =
  "Let's ship the cross-platform build this week and write the release notes.";

// A looping, non-interactive demo of a dictation: listen → transcribe → insert.
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

    let timers: ReturnType<typeof setTimeout>[] = [];
    let cancelled = false;
    const push = (fn: () => void, ms: number) => timers.push(setTimeout(fn, ms));

    function cycle() {
      if (cancelled) return;
      setTyped("");
      setDone(false);
      setMode("listening");
      // Stream the words in while "listening".
      const words = SAMPLE.split(" ");
      words.forEach((_, i) => {
        push(() => {
          setTyped(words.slice(0, i + 1).join(" "));
        }, 280 + i * 150);
      });
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

export function Hero() {
  const { mode, typed, done } = useDemo();

  return (
    <section className={styles.hero}>
      <div className={`container ${styles.grid}`}>
        <div className={styles.copy}>
          <Tag>100% on-device · no cloud</Tag>
          <h1 className={styles.title}>
            Talk. It types.
            <br />
            <span className={styles.titleAccent}>Nothing leaves your Mac or PC.</span>
          </h1>
          <p className={`lead ${styles.lead}`}>
            Hold a key, speak, release — your words are transcribed locally and
            pasted right at your cursor, in any app. No account, no network, no
            audio ever sent anywhere.
          </p>

          <div className={styles.actions}>
            <DownloadCTA />
          </div>

          <p className={styles.hint}>
            Hold <Kbd>fn</Kbd> on Mac · <Kbd>Left&nbsp;Ctrl</Kbd> on Windows.
            Free &amp; open source.
          </p>
        </div>

        <div className={styles.demo} aria-hidden="false">
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
      </div>
    </section>
  );
}
