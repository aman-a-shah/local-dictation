type Props = {
  size?: number;
  withWordmark?: boolean;
  className?: string;
  /**
   * Render the *app* mark (white bars on a Big-Sur squircle) instead of the
   * website mark (gold bars). The two are deliberately different — the macOS
   * icon is white — so the in-app dashboard passes this to match the dock /
   * menu-bar icon exactly, while the website keeps its gold logo. Geometry here
   * mirrors assets/make_icon.py (the icon's source of truth): the same 5-bar
   * waveform on the 32-grid, mapped into an inset squircle with Apple's corner
   * ratio.
   */
  appMark?: boolean;
};

// Shared 32-unit waveform grid (identical to assets/make_icon.py + the gold mark).
const BARS: [number, number][] = [
  [8, 11],
  [12, 6],
  [16, 16],
  [20, 8],
  [24, 12],
];

// App-icon squircle proportions (Apple Big Sur): artwork sits inside a margin,
// with a continuous-ish corner radius — see make_icon.py.
const INSET = 32 * 0.098; // canvas margin on each side
const SIDE = 32 - 2 * INSET; // squircle side
const SCALE = SIDE / 32; // map the 32-grid onto the inset squircle
const RADIUS = SIDE * 0.2237;
const BAR_W = 2.8 * SCALE;

/**
 * Brand mark: a compact 5-bar waveform inside a rounded square (reads as "voice"
 * the way the menu-bar glyph does), optionally followed by the wordmark. Gold by
 * default (website); pass `appMark` for the white-on-squircle macOS app icon.
 */
export function Logo({ size = 28, withWordmark = true, className, appMark }: Props) {
  return (
    <span
      className={className}
      style={{ display: "inline-flex", alignItems: "center", gap: "0.6em" }}
    >
      <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true">
        {appMark ? (
          <>
            <rect
              x={INSET}
              y={INSET}
              width={SIDE}
              height={SIDE}
              rx={RADIUS}
              fill="var(--ink-strong, #19191f)"
            />
            {BARS.map(([cx, h], i) => {
              const bh = h * SCALE;
              return (
                <rect
                  key={i}
                  x={INSET + cx * SCALE - BAR_W / 2}
                  y={16 - bh / 2}
                  width={BAR_W}
                  height={bh}
                  rx={BAR_W / 2}
                  fill="#fff"
                />
              );
            })}
          </>
        ) : (
          <>
            <rect x="0.5" y="0.5" width="31" height="31" rx="8" fill="var(--ink-strong, #19191f)" />
            {BARS.map(([x, h], i) => (
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
          </>
        )}
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
