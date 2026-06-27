import styles from "./Comparison.module.css";

type Cell = boolean | string;
const COLS = ["Voca", "Cloud dictation", "Built-in OS"];
const ROWS: { feature: string; cells: [Cell, Cell, Cell] }[] = [
  { feature: "Audio never leaves your device", cells: [true, false, "varies"] },
  { feature: "Works fully offline", cells: [true, false, "partly"] },
  { feature: "Pastes into any app", cells: [true, true, "partly"] },
  { feature: "No account or sign-in", cells: [true, false, true] },
  { feature: "Remappable push-to-talk key", cells: [true, "varies", false] },
  { feature: "Spoken lists → formatted lists", cells: [true, false, false] },
  { feature: "Private on-device history", cells: [true, false, false] },
  { feature: "Free & open source", cells: [true, false, "—"] },
];

function Mark({ v }: { v: Cell }) {
  if (v === true)
    return (
      <span className={`${styles.yes} ld-shimmer`} aria-label="Yes">
        <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
          <path d="M3.5 8.5l3 3 6-7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
    );
  if (v === false)
    return (
      <span className={styles.no} aria-label="No">
        <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
          <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        </svg>
      </span>
    );
  return <span className={styles.partial}>{v}</span>;
}

export function Comparison() {
  return (
    <div className={styles.scroll}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th className={styles.featureHead} scope="col"></th>
            {COLS.map((c, i) => (
              <th key={c} scope="col" className={i === 0 ? styles.ownCol : ""}>
                {c}
                {i === 0 && <span className={styles.ownBadge}>You’re here</span>}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ROWS.map((r) => (
            <tr key={r.feature}>
              <th scope="row" className={styles.rowHead}>{r.feature}</th>
              {r.cells.map((c, i) => (
                <td key={i} className={i === 0 ? styles.ownCol : ""}>
                  <Mark v={c} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
