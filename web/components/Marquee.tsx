import styles from "./Marquee.module.css";

/** A seamless auto-scrolling row (pauses on hover). Used for "works everywhere". */
export function Marquee({ items }: { items: string[] }) {
  const doubled = [...items, ...items];
  return (
    <div className={styles.wrap} aria-label={`Works in ${items.join(", ")}`}>
      <div className={styles.track}>
        {doubled.map((it, i) => (
          <span key={i} className={styles.item} aria-hidden={i >= items.length}>
            {it}
          </span>
        ))}
      </div>
      <div className={styles.fadeL} aria-hidden="true" />
      <div className={styles.fadeR} aria-hidden="true" />
    </div>
  );
}
