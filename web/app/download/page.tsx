import type { Metadata } from "next";
import { Kbd } from "@local-dictation/ui";
import { DownloadChooser } from "@/components/DownloadChooser";
import { getLatestRelease, RELEASES_REPO } from "@/lib/releases";
import styles from "./download.module.css";

export const metadata: Metadata = {
  title: "Download",
  description:
    "Download Local Dictation for macOS (Apple Silicon or Intel) and Windows. Free, open source, 100% on-device.",
};

export default async function DownloadPage() {
  const release = await getLatestRelease();

  return (
    <div className="container container--narrow section">
      <header className={styles.head}>
        <h1 className={styles.h1}>Download Local Dictation</h1>
        <p className="lead">
          Free and open source. Version{" "}
          <span className={styles.version}>{release.version}</span>. We highlight
          the build for your device — every platform is listed below.
        </p>
      </header>

      <DownloadChooser />

      <p className={styles.firstrun}>
        First launch downloads the speech model once (~1.6&nbsp;GB on Apple
        Silicon, smaller on CPU), then everything runs offline.
      </p>

      <section className={styles.install}>
        <h2 className={styles.h2}>Opening the app the first time</h2>
        <p className={styles.note}>
          Builds aren’t code-signed yet, so the OS shows a one-time warning. This
          is expected for a small open-source app — here’s how to get past it.
        </p>
        <div className={styles.osGuides}>
          <div className={styles.guide}>
            <h3 className={styles.guideTitle}>macOS</h3>
            <ol className={styles.steps}>
              <li>Open the <span className={styles.mono}>.dmg</span> and drag the app to Applications.</li>
              <li>Right-click the app → <strong>Open</strong> → <strong>Open</strong> again.</li>
              <li>Allow <strong>Microphone</strong> when asked, and add the app under System Settings → Privacy &amp; Security → <strong>Accessibility</strong>.</li>
              <li>Hold <Kbd>fn</Kbd>, speak, release.</li>
            </ol>
          </div>
          <div className={styles.guide}>
            <h3 className={styles.guideTitle}>Windows <span className={styles.badge}>Beta</span></h3>
            <ol className={styles.steps}>
              <li>Run <span className={styles.mono}>LocalDictationSetup…exe</span>.</li>
              <li>If SmartScreen appears: <strong>More info</strong> → <strong>Run anyway</strong>.</li>
              <li>Finish the installer; the app starts in your system tray.</li>
              <li>Hold <Kbd>Left&nbsp;Ctrl</Kbd>, speak, release.</li>
            </ol>
          </div>
        </div>
        <p className={styles.verify}>
          Prefer to verify the download? Each release publishes SHA-256 checksums
          on{" "}
          <a href={`https://github.com/${RELEASES_REPO}/releases/latest`}>the releases page</a>.
        </p>
      </section>

      <section className={styles.reqs}>
        <h2 className={styles.h2}>System requirements</h2>
        <ul className={styles.reqList}>
          <li><strong>macOS</strong> 13 Ventura or later — Apple Silicon (GPU/MLX) or Intel (CPU).</li>
          <li><strong>Windows</strong> 10 or 11, 64-bit (<strong>beta</strong> — actively being tested). A discrete NVIDIA GPU is used automatically if present.</li>
          <li>~2 GB free disk for the speech model. A microphone. No internet required after setup.</li>
        </ul>
      </section>
    </div>
  );
}
