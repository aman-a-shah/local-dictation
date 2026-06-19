import Link from "next/link";
import { Kbd, ButtonLink, Stat, CountUp } from "@local-dictation/ui";
import { Hero } from "@/components/Hero";
import { Reveal } from "@/components/Reveal";
import { Marquee } from "@/components/Marquee";
import { FeatureTabs } from "@/components/FeatureTabs";
import { Comparison } from "@/components/Comparison";
import { getLatestRelease } from "@/lib/releases";
import styles from "./page.module.css";

const APPS = [
  "VS Code", "Slack", "Gmail", "Notion", "Terminal", "Google Docs", "Figma",
  "ChatGPT", "Obsidian", "Linear", "Messages", "Word", "Cursor", "Discord",
];

export default async function Home() {
  const release = await getLatestRelease();

  return (
    <>
      <Hero />

      {/* ---- Works everywhere (marquee) ---- */}
      <section className={`${styles.marqueeBand}`}>
        <div className="container">
          <p className={styles.marqueeLabel}>Types straight into the apps you already use</p>
          <Marquee items={APPS} />
        </div>
      </section>

      {/* ---- How it works ---- */}
      <Reveal>
        <section id="how" className="section container">
          <div className={styles.sectionHead}>
            <h2 className={styles.h2}>Three seconds, start to cursor.</h2>
            <p className="lead">
              No window to focus, no “record” button. It lives in your menu bar /
              tray and listens only while you hold the key.
            </p>
          </div>

          <ol className={styles.steps}>
            <li className="ld-reveal">
              <div className={styles.stepIcon}><IconKey /></div>
              <span className={styles.stepNum}>01</span>
              <h3 className={styles.stepTitle}>Hold the key</h3>
              <p className={styles.stepText}>
                Press and hold <Kbd>fn</Kbd> on Mac or <Kbd>Left&nbsp;Ctrl</Kbd> on
                Windows. The mic opens instantly — only while held.
              </p>
            </li>
            <li className="ld-reveal" style={{ ["--reveal-delay" as string]: "90ms" }}>
              <div className={styles.stepIcon}><IconWave /></div>
              <span className={styles.stepNum}>02</span>
              <h3 className={styles.stepTitle}>Speak naturally</h3>
              <p className={styles.stepText}>
                Talk at a normal pace. A waveform shows it’s hearing you. Every
                sample stays on the device.
              </p>
            </li>
            <li className="ld-reveal" style={{ ["--reveal-delay" as string]: "180ms" }}>
              <div className={styles.stepIcon}><IconCursor /></div>
              <span className={styles.stepNum}>03</span>
              <h3 className={styles.stepTitle}>Release to insert</h3>
              <p className={styles.stepText}>
                Let go. Whisper transcribes locally and the text is pasted right
                where your cursor is — formatted and ready.
              </p>
            </li>
          </ol>
        </section>
      </Reveal>

      {/* ---- Interactive feature showcase ---- */}
      <Reveal>
        <section className={styles.showcase}>
          <div className="container">
            <div className={styles.sectionHead}>
              <h2 className={styles.h2}>One small tool. A lot of range.</h2>
              <p className="lead">Click through what it actually does.</p>
            </div>
            <div className="ld-reveal">
              <FeatureTabs />
            </div>
          </div>
        </section>
      </Reveal>

      {/* ---- Privacy band (BLACK) ---- */}
      <section id="privacy" className={`${styles.privacy} ld-on-dark ld-grain`}>
        <div className="container">
          <div className={styles.privacyGrid}>
            <Reveal>
              <div className="ld-reveal">
                <p className={styles.kicker}>The whole point</p>
                <h2 className={styles.h2Dark}>
                  Your voice never leaves the&nbsp;machine.
                </h2>
                <p className={styles.leadDark}>
                  There’s no server to send audio to, because there is no server.
                  Transcription runs on your own CPU/GPU with Whisper. No account,
                  no API key, no telemetry. The only thing that ever touches the
                  network is an optional update check (version &amp; OS — nothing
                  else), which you can turn off.
                </p>
                <div className={styles.assurances}>
                  {["No network calls", "No account", "No telemetry", "Open source"].map((a) => (
                    <span key={a}>{a}</span>
                  ))}
                </div>
              </div>
            </Reveal>

            <Reveal>
              <div className={`${styles.flow} ld-reveal`} aria-hidden="true">
                <div className={styles.flowNode}><IconMic /> Your voice</div>
                <div className={styles.flowArrow}>↓</div>
                <div className={`${styles.flowNode} ${styles.flowChip}`}>
                  On-device Whisper
                  <span className={styles.flowChipSub}>your CPU / GPU</span>
                </div>
                <div className={styles.flowArrow}>↓</div>
                <div className={styles.flowNode}><IconCursor /> Text at your cursor</div>
                <div className={styles.flowCloud}>cloud — never used</div>
              </div>
            </Reveal>
          </div>
        </div>
      </section>

      {/* ---- Speed / benchmark ---- */}
      <Reveal>
        <section className="section container">
          <div className={styles.sectionHead}>
            <h2 className={styles.h2}>Faster than your fastest typing.</h2>
            <p className="lead">
              Speaking runs about 150 words per minute; sustained typing about 40.
              Transcription is near-instant on Apple Silicon.
            </p>
          </div>

          <div className={`${styles.bench} ld-reveal`}>
            <div className={styles.benchRow}>
              <span className={styles.benchLabel}>Typing</span>
              <div className={styles.benchTrack}><div className={styles.benchFill} style={{ width: "27%" }} /></div>
              <span className={styles.benchVal}>~40 wpm</span>
            </div>
            <div className={styles.benchRow}>
              <span className={styles.benchLabel}>Dictation</span>
              <div className={styles.benchTrack}><div className={`${styles.benchFill} ${styles.benchGold}`} style={{ width: "100%" }} /></div>
              <span className={styles.benchVal}>~150 wpm</span>
            </div>
          </div>

          <div className={styles.statsRow}>
            <div className="ld-reveal"><Stat value={<><CountUp end={10} />–<CountUp end={20} />×</>} label="faster than real time (Apple Silicon)" /></div>
            <div className="ld-reveal" style={{ ["--reveal-delay" as string]: "80ms" }}><Stat value="0" label="bytes of audio uploaded, ever" /></div>
            <div className="ld-reveal" style={{ ["--reveal-delay" as string]: "160ms" }}><Stat value={<CountUp end={40} suffix="+" />} label="languages, auto-detected" /></div>
            <div className="ld-reveal" style={{ ["--reveal-delay" as string]: "240ms" }}><Stat value="∞" label="free — open source, no subscription" /></div>
          </div>
          <p className={styles.specNote}>
            Apple Silicon runs <code>whisper-large-v3-turbo</code> on the GPU via
            Apple MLX. Intel Macs and Windows use faster-whisper on the CPU (with a
            snappier default model). The model is warmed at launch, so your first
            take is already fast.
          </p>
        </section>
      </Reveal>

      {/* ---- Built for ---- */}
      <Reveal>
        <section className={styles.personasBand}>
          <div className="container">
            <div className={styles.sectionHead}>
              <h2 className={styles.h2}>Built for people who’d rather talk.</h2>
            </div>
            <div className={styles.personas}>
              {[
                { i: <IconCode />, t: "Developers", d: "Dictate comments, commit messages, and prompts without leaving the keyboard home row." },
                { i: <IconPen />, t: "Writers", d: "Draft at the speed of thought, then edit. Spoken lists come out as real lists." },
                { i: <IconSearch />, t: "Researchers", d: "Capture notes and ideas the moment they land — privately, with searchable history." },
                { i: <IconHand />, t: "RSI & accessibility", d: "A genuinely fast typing alternative that never sends your voice to the cloud." },
              ].map((p, idx) => (
                <article key={p.t} className={`${styles.persona} ld-reveal`} style={{ ["--reveal-delay" as string]: `${idx * 70}ms` }}>
                  <div className={styles.personaIcon}>{p.i}</div>
                  <h3 className={styles.personaTitle}>{p.t}</h3>
                  <p className={styles.personaText}>{p.d}</p>
                </article>
              ))}
            </div>
          </div>
        </section>
      </Reveal>

      {/* ---- Comparison ---- */}
      <Reveal>
        <section className="section container">
          <div className={styles.sectionHead}>
            <h2 className={styles.h2}>How it compares.</h2>
            <p className="lead">Most dictation either ships your audio to a server or only half-works outside one app.</p>
          </div>
          <div className="ld-reveal"><Comparison /></div>
        </section>
      </Reveal>

      {/* ---- FAQ teaser ---- */}
      <Reveal>
        <section className={styles.faqBand}>
          <div className="container">
            <div className={styles.faqGrid}>
              <div>
                <h2 className={styles.h2}>Good questions.</h2>
                <p className="lead">The short answers — the rest live on the FAQ.</p>
                <Link href="/faq" className={styles.faqLink}>Read the full FAQ →</Link>
              </div>
              <div className={styles.faqList}>
                {[
                  ["Does my audio leave the device?", "Never. It’s transcribed locally and discarded. The only network call is an optional update check (version + OS)."],
                  ["Which key do I hold?", "fn on macOS, Left Ctrl on Windows (fn can’t be detected there). Both are remappable."],
                  ["Why the security warning on launch?", "Builds aren’t signed yet. Right-click → Open on Mac; “More info → Run anyway” on Windows."],
                ].map(([q, a]) => (
                  <div key={q} className={`${styles.faqItem} ld-reveal`}>
                    <h3 className={styles.faqQ}>{q}</h3>
                    <p className={styles.faqA}>{a}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      </Reveal>

      {/* ---- Final CTA ---- */}
      <section className={`${styles.cta} ld-on-dark ld-grain`}>
        <div className="container">
          <h2 className={styles.ctaTitle}>Stop typing what you could say.</h2>
          <p className={styles.leadDark} style={{ marginInline: "auto", textAlign: "center" }}>
            Free, open source, and private by design. v{release.version}.
          </p>
          <div className={styles.ctaButtons}>
            <ButtonLink size="lg" href="/download">Download for your platform</ButtonLink>
            <ButtonLink size="lg" variant="ghost" href="/faq">Read the FAQ</ButtonLink>
          </div>
        </div>
      </section>
    </>
  );
}

/* ---- Inline line icons (gold via currentColor) ---- */
const I = { width: 22, height: 22, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.6, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
function IconKey() { return <svg {...I}><circle cx="8" cy="15" r="4" /><path d="M11 12l8-8M16 4l3 3M14 6l2 2" /></svg>; }
function IconWave() { return <svg {...I}><path d="M4 12h2M9 7v10M14 4v16M19 9v6M22 11h0" /></svg>; }
function IconCursor() { return <svg {...I}><path d="M5 3l6 16 2-6 6-2z" /></svg>; }
function IconMic() { return <svg {...I}><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" /></svg>; }
function IconCode() { return <svg {...I}><path d="M8 8l-4 4 4 4M16 8l4 4-4 4M13 5l-2 14" /></svg>; }
function IconPen() { return <svg {...I}><path d="M4 20l4-1 11-11-3-3L5 16z" /></svg>; }
function IconSearch() { return <svg {...I}><circle cx="11" cy="11" r="6" /><path d="M20 20l-4-4" /></svg>; }
function IconHand() { return <svg {...I}><path d="M8 11V5a1.5 1.5 0 0 1 3 0v5m0 0V4a1.5 1.5 0 0 1 3 0v6m0 0V6a1.5 1.5 0 0 1 3 0v8a6 6 0 0 1-6 6h-1a5 5 0 0 1-4-2l-3-4a1.6 1.6 0 0 1 2.4-2L8 13" /></svg>; }
