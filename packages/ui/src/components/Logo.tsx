type Props = { size?: number; withWordmark?: boolean; className?: string };

/**
 * Brand mark: a compact rose waveform inside a rounded square (reads as "voice"
 * the way the menu-bar glyph does), optionally followed by the wordmark.
 */
export function Logo({ size = 28, withWordmark = true, className }: Props) {
  return (
    <span
      className={className}
      style={{ display: "inline-flex", alignItems: "center", gap: "0.6em" }}
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 32 32"
        fill="none"
        aria-hidden="true"
      >
        <rect x="0.5" y="0.5" width="31" height="31" rx="8" fill="var(--ink-strong, #19191f)" />
        {[
          [8, 11],
          [12, 6],
          [16, 16],
          [20, 8],
          [24, 12],
        ].map(([x, h], i) => (
          <rect
            key={i}
            x={x - 1.4}
            y={16 - h / 2}
            width="2.8"
            height={h}
            rx="1.4"
            fill="var(--gold, #d4af37)"
          />
        ))}
      </svg>
      {withWordmark && (
        <span
          style={{
            fontWeight: 600,
            letterSpacing: "-0.02em",
            fontSize: "1.02rem",
          }}
        >
          Local Dictation
        </span>
      )}
    </span>
  );
}
