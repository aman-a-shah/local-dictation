import type { Metadata } from "next";
import { marked } from "marked";
import { getLatestRelease, REPO } from "@/lib/releases";
import styles from "./changelog.module.css";

export const metadata: Metadata = {
  title: "Changelog",
  description: "What's new in Local Dictation.",
};

export default async function ChangelogPage() {
  const release = await getLatestRelease();
  const notesHtml = release.notes
    ? (marked.parse(release.notes, { async: false }) as string)
    : "";

  return (
    <div className="container container--narrow section">
      <header className={styles.head}>
        <h1 className={styles.h1}>Changelog</h1>
        <p className="lead">Release notes for every build.</p>
      </header>

      <article className={styles.release}>
        <div className={styles.relHead}>
          <h2 className={styles.version}>v{release.version}</h2>
          {release.publishedAt && (
            <time className={styles.date}>
              {new Date(release.publishedAt).toLocaleDateString(undefined, {
                year: "numeric",
                month: "long",
                day: "numeric",
              })}
            </time>
          )}
        </div>
        {notesHtml ? (
          <div className="prose" dangerouslySetInnerHTML={{ __html: notesHtml }} />
        ) : (
          <p className={styles.empty}>
            The first public release. Push-to-talk dictation, fully on-device,
            for macOS (Apple Silicon &amp; Intel) and Windows, with a private
            dashboard.
          </p>
        )}
      </article>

      <p className={styles.all}>
        Full history on{" "}
        <a href={`https://github.com/${REPO}/releases`}>GitHub Releases</a>.
      </p>
    </div>
  );
}
