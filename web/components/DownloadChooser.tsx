"use client";

import { ButtonLink, useDetectedOS } from "@local-dictation/ui";
import type { DetectedOS } from "@local-dictation/ui";
import { BUILDS, type BuildKey } from "@/lib/releases";
import styles from "./DownloadChooser.module.css";

const ORDER: BuildKey[] = ["mac-arm64", "mac-x64", "windows-x64"];

const DETECT_TO_KEY: Record<string, BuildKey> = {
  "mac-arm64": "mac-arm64",
  "mac-x64": "mac-x64",
  windows: "windows-x64",
};

function osIcon(key: BuildKey) {
  return key.startsWith("mac") ? "" : "⊞";
}

export function DownloadChooser() {
  const os: DetectedOS = useDetectedOS();
  const recommended = DETECT_TO_KEY[os] ?? null;

  return (
    <div className={styles.list}>
      {ORDER.map((key) => {
        const b = BUILDS[key];
        const isRec = key === recommended;
        return (
          <div
            key={key}
            className={`${styles.row} ${isRec ? styles.recommended : ""}`}
          >
            <div className={styles.meta}>
              <span className={styles.icon} aria-hidden="true">
                {osIcon(key)}
              </span>
              <div>
                <div className={styles.label}>
                  {b.label}
                  {isRec && <span className={`${styles.badge} ld-shimmer`}>Detected</span>}
                </div>
                <div className={styles.sub}>
                  {b.sublabel} · <span className={styles.mono}>{b.asset}</span>
                </div>
              </div>
            </div>
            <ButtonLink
              variant={isRec ? "primary" : "ghost"}
              href={`/api/download?os=${b.platform}&arch=${b.arch}`}
            >
              Download {b.ext}
            </ButtonLink>
          </div>
        );
      })}
    </div>
  );
}
