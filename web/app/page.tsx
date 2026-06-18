import { Kbd, ButtonLink, Stat, CountUp } from "@local-dictation/ui";
import { Hero } from "@/components/Hero";
import { Reveal } from "@/components/Reveal";
import { getLatestRelease } from "@/lib/releases";
import styles from "./page.module.css";

export default async function Home() {
  const release = await getLatestRelease();

  return (
    <>
      <Hero />

      <Reveal>
        {/* ---- How it works: a real 3-step sequence ---- */}
        <section id="how" className="section container">
          <div className={styles.sectionHead}>
            <h2 className={styles.h2}>Three seconds, start to cursor.</h2>
            <p className="lead">
              No window to focus, no “start recording” button. It lives in your
              menu bar / tray and listens only while you hold the key.
            </p>
          </div>

          <ol className={styles.steps}>
            <li className="ld-reveal">
              <span className={styles.stepNum}>01</span>
              <h3 className={styles.stepTitle}>Hold the key</h3>
              <p className={styles.stepText}>
                Press and hold <Kbd>fn</Kbd> on Mac or <Kbd>Left&nbsp;Ctrl</Kbd>{" "}
                on Windows. The mic opens instantly — only while held.
              </p>
            </li>
            <li className="ld-reveal" style={{ ["--reveal-delay" as string]: "90ms" }}>
              <span className={styles.stepNum}>02</span>
              <h3 className={styles.stepTitle}>Speak naturally</h3>
              <p className={styles.stepText}>
                Talk at a normal pace. A waveform under the notch / in the tray
                shows it’s hearing you. Everything stays on the device.
              </p>
            </li>
            <li className="ld-reveal" style={{ ["--reveal-delay" as string]: "180ms" }}>
              <span className={styles.stepNum}>03</span>
              <h3 className={styles.stepTitle}>Release to insert</h3>
              <p className={styles.stepText}>
                Let go. Whisper transcribes locally and the text is pasted right
                where your cursor is — in any app, formatted and ready.
              </p>
            </li>
          </ol>
        </section>
      </Reveal>

      <Reveal>
        {/* ---- Privacy: the promise made felt ---- */}
        <section id="privacy" className={styles.privacy}>
          <div className="container">
            <div className={styles.privacyGrid}>
              <div className="ld-reveal">
                <p className={styles.kicker}>The whole point</p>
                <h2 className={styles.h2}>
                  Your voice never leaves the&nbsp;machine.
                </h2>
                <p className="lead">
                  There’s no server to send audio to, because there is no server.
                  Transcription runs on your own CPU/GPU with Whisper. No account,
                  no API key, no telemetry. The only thing that ever touches the
                  network is an optional update check (version &amp; OS — nothing
                  else), which you can turn off.
                </p>
                <div className={styles.assurances}>
                  <span>No network calls</span>
                  <span>No account</span>
                  <span>No telemetry</span>
                  <span>Open source</span>
                </div>
              </div>

              <div className={`${styles.flow} ld-reveal`} aria-hidden="true">
                <div className={styles.flowNode}>🎙️ Your voice</div>
                <div className={styles.flowArrow}>↓</div>
                <div className={`${styles.flowNode} ${styles.flowChip}`}>
                  On-device Whisper
                  <span className={styles.flowChipSub}>your CPU / GPU</span>
                </div>
                <div className={styles.flowArrow}>↓</div>
                <div className={styles.flowNode}>⌨️ Text at your cursor</div>
                <div className={styles.flowCloud}>☁ cloud — never used</div>
              </div>
            </div>
          </div>
        </section>
      </Reveal>

      <Reveal>
        {/* ---- Speed / specs as an instrument readout ---- */}
        <section className="section container">
          <div className={styles.statsRow}>
            <div className="ld-reveal">
              <Stat value="10–20×" label="faster than real time on Apple Silicon" />
            </div>
            <div className="ld-reveal" style={{ ["--reveal-delay" as string]: "80ms" }}>
              <Stat value="0" label="bytes of audio uploaded, ever" />
            </div>
            <div className="ld-reveal" style={{ ["--reveal-delay" as string]: "160ms" }}>
              <Stat value="∞" label="free — no subscription, open source" />
            </div>
            <div className="ld-reveal" style={{ ["--reveal-delay" as string]: "240ms" }}>
              <Stat value={<CountUp end={40} suffix="+" />} label="languages, auto-detected" />
            </div>
          </div>
          <p className={styles.specNote}>
            Apple Silicon runs <code>whisper-large-v3-turbo</code> on the GPU via
            Apple MLX. Intel Macs and Windows use faster-whisper on the CPU
            (with a snappier default model). The model is warmed at launch, so
            your first take is already fast.
          </p>
        </section>
      </Reveal>

      <Reveal>
        {/* ---- Features: varied, not identical cards ---- */}
        <section className="section container">
          <div className={styles.sectionHead}>
            <h2 className={styles.h2}>Small, fast, and genuinely yours.</h2>
          </div>
          <div className={styles.features}>
            <article className={`${styles.feature} ${styles.featureWide} ld-reveal`}>
              <h3 className={styles.featureTitle}>Works in every app</h3>
              <p className={styles.featureText}>
                It pastes at the system cursor, so it works the same in your
                editor, your browser, Slack, email, a terminal — anywhere you can
                type. Unicode-safe: accents, emoji, and CJK all land correctly.
              </p>
            </article>

            <article className={`${styles.feature} ld-reveal`}>
              <h3 className={styles.featureTitle}>Spoken lists become real lists</h3>
              <p className={styles.featureText}>
                A fast, rule-based polish pass cleans transcripts with no added
                latency.
              </p>
              <pre className={styles.code}>
                <span className={styles.codeDim}>“my list is milk, eggs, bread”</span>
                {"\n→ my list:\n   1. milk\n   2. eggs\n   3. bread"}
              </pre>
            </article>

            <article className={`${styles.feature} ld-reveal`}>
              <h3 className={styles.featureTitle}>A private dashboard</h3>
              <p className={styles.featureText}>
                Launch the app to a dashboard of your recent transcriptions, total
                words, time saved, and streak — stored only on your device.
              </p>
            </article>

            <article className={`${styles.feature} ${styles.featureWide} ld-reveal`}>
              <h3 className={styles.featureTitle}>Your key, your model, your rules</h3>
              <p className={styles.featureText}>
                Remap the push-to-talk key, switch the Whisper model for
                speed vs. accuracy, force a language, toggle sounds and history —
                all in settings. Sensible defaults out of the box.
              </p>
            </article>
          </div>
        </section>
      </Reveal>

      {/* ---- Final CTA ---- */}
      <section className={styles.cta}>
        <div className="container">
          <h2 className={styles.ctaTitle}>Stop typing what you could say.</h2>
          <p className="lead" style={{ marginInline: "auto", textAlign: "center" }}>
            Free, open source, and private by design. v{release.version}.
          </p>
          <div className={styles.ctaButtons}>
            <ButtonLink size="lg" href="/download">
              Download for your platform
            </ButtonLink>
            <ButtonLink size="lg" variant="ghost" href="/faq">
              Read the FAQ
            </ButtonLink>
          </div>
        </div>
      </section>
    </>
  );
}
