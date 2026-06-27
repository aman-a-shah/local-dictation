"use client";

import { useState } from "react";
import { Kbd } from "@voca/ui";
import styles from "./FeatureTabs.module.css";

type Tab = { id: string; label: string; blurb: string; preview: React.ReactNode };

const TABS: Tab[] = [
  {
    id: "anywhere",
    label: "Paste anywhere",
    blurb:
      "It types at the system cursor, so it works identically in your editor, browser, chat, email, or terminal — no integrations, no plugins.",
    preview: (
      <div className={styles.appMock}>
        <div className={styles.appTabs}>
          <span className={styles.appTabActive}>main.py</span>
          <span>README.md</span>
          <span>notes.txt</span>
        </div>
        <pre className={styles.appCode}>
{`def summary():
    """`}<span className={styles.typed}>Return a short, plain-language recap of the run.</span>{`"""
    ...`}<span className={styles.cursor} />
        </pre>
      </div>
    ),
  },
  {
    id: "format",
    label: "Smart formatting",
    blurb:
      "A fast, rule-based pass cleans transcripts as they land — spoken enumerations become real lists, with zero added latency.",
    preview: (
      <div className={styles.fmt}>
        <div className={styles.fmtSay}>
          <span className={styles.fmtLabel}>you say</span>
          “my plan is research, draft, and ship”
        </div>
        <div className={styles.fmtArrow}>↓</div>
        <div className={styles.fmtOut}>
          <span className={styles.fmtLabel}>you get</span>
          my plan:
          {"\n"}1. research
          {"\n"}2. draft
          {"\n"}3. ship
        </div>
      </div>
    ),
  },
  {
    id: "dashboard",
    label: "Private dashboard",
    blurb:
      "Launch the app to a dashboard of your recent dictations, total words, time saved, and streak — stored only on your device.",
    preview: (
      <div className={styles.dash}>
        <div className={styles.dashStats}>
          <div><b>8,690</b><span>words</span></div>
          <div><b>3h 37m</b><span>saved</span></div>
          <div><b>9</b><span>day streak</span></div>
        </div>
        <div className={styles.dashChart}>
          {[40, 78, 55, 66, 90, 48, 72, 84, 60, 95].map((h, i) => (
            <span key={i} style={{ height: `${h}%` }} />
          ))}
        </div>
      </div>
    ),
  },
  {
    id: "shortcuts",
    label: "Your shortcuts",
    blurb:
      "Remap the push-to-talk key, switch models for speed vs. accuracy, pin a language, toggle sounds — sensible defaults, fully yours.",
    preview: (
      <div className={styles.settings}>
        <div className={styles.setRow}><span>Push-to-talk</span><Kbd>fn</Kbd></div>
        <div className={styles.setRow}><span>Model</span><code>large-v3-turbo</code></div>
        <div className={styles.setRow}><span>Language</span><code>auto-detect</code></div>
        <div className={styles.setRow}><span>Smart formatting</span><i className={styles.on} /></div>
        <div className={styles.setRow}><span>Run at login</span><i className={styles.on} /></div>
      </div>
    ),
  },
];

export function FeatureTabs() {
  const [active, setActive] = useState(0);
  const tab = TABS[active];
  return (
    <div className={styles.wrap}>
      <div className={styles.tabs} role="tablist" aria-label="Features">
        {TABS.map((t, i) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={i === active}
            className={`${styles.tab} ${i === active ? styles.tabActive : ""}`}
            onClick={() => setActive(i)}
          >
            <span className={styles.tabLabel}>{t.label}</span>
            <span className={styles.tabBlurb}>{t.blurb}</span>
          </button>
        ))}
      </div>
      <div className={styles.previewPane} key={tab.id}>
        {tab.preview}
      </div>
    </div>
  );
}
