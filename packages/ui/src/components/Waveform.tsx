"use client";

import { useEffect, useRef } from "react";

export type WaveMode = "idle" | "listening" | "thinking" | "done";

type Props = {
  mode?: WaveMode;
  bars?: number;
  height?: number;
  /** Optional live 0..1 level (dashboard real-time mic); overrides synthetic motion. */
  level?: number;
  className?: string;
  /** Multiplier on bar amplitude (hero wants taller). */
  intensity?: number;
};

// Gold = the voice; champagne = listening; a faint green confirm.
const ACCENT = "oklch(0.8 0.13 88)";
const LIVE = "oklch(0.92 0.07 96)";
const MINT = "oklch(0.74 0.14 150)";

function prefersReducedMotion() {
  return (
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
  );
}

/**
 * The brand hero object: a row of thin bars that breathe like a live voice
 * meter. Rose at rest, cyan while listening, a calmer travelling pulse while
 * "thinking". Pure canvas + rAF, no deps. Reduced-motion renders a static,
 * representative profile (never blank).
 */
export function Waveform({
  mode = "idle",
  bars = 48,
  height = 140,
  level,
  className,
  intensity = 1,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const modeRef = useRef(mode);
  const levelRef = useRef(level);
  modeRef.current = mode;
  levelRef.current = level;

  useEffect(() => {
    const cv = canvasRef.current;
    if (!cv) return;
    const cx = cv.getContext("2d");
    if (!cx) return;

    let raf = 0;
    let running = true;
    const reduced = prefersReducedMotion();
    const heights = new Float32Array(bars).fill(0.2);

    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = cv!.clientWidth || 600;
      cv!.width = Math.round(w * dpr);
      cv!.height = Math.round(height * dpr);
      cx!.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(cv);

    function color(m: WaveMode): string {
      if (m === "listening") return LIVE;
      if (m === "done") return MINT;
      return ACCENT;
    }

    function target(i: number, t: number, m: WaveMode): number {
      const live = levelRef.current;
      const center = 1 - Math.abs(i / (bars - 1) - 0.5) * 2; // tent: tall middle
      const shape = 0.25 + center * 0.75;
      if (live != null) {
        return Math.min(1, (0.12 + live * 1.6) * shape);
      }
      if (m === "thinking") {
        const pulse = 0.5 + 0.5 * Math.sin(t * 2.2 - i * 0.5);
        return (0.18 + pulse * 0.28) * shape;
      }
      const speed = m === "listening" ? 5.2 : 3.0;
      const amp = m === "listening" ? 0.9 : 0.62;
      const v =
        0.5 +
        0.32 * Math.sin(t * speed + i * 0.55) +
        0.2 * Math.sin(t * (speed * 0.6) + i * 0.9 + 1.7) +
        0.12 * Math.sin(t * (speed * 1.7) + i * 0.3);
      return Math.max(0.06, Math.min(1, v * amp * shape));
    }

    function draw(time: number) {
      if (!running) return;
      const t = time / 1000;
      const m = modeRef.current;
      const w = cv!.clientWidth || 600;
      const h = height;
      cx!.clearRect(0, 0, w, h);

      const gap = Math.max(2, w / bars / 3.2);
      const bw = (w - gap * (bars - 1)) / bars;
      const mid = h / 2;
      cx!.fillStyle = color(m);

      for (let i = 0; i < bars; i++) {
        const tgt = reduced ? target(i, 1.2, "idle") : target(i, t, m);
        heights[i] += (tgt - heights[i]) * (reduced ? 1 : 0.18);
        const norm = heights[i];
        const bh = Math.max(bw, norm * (h - 6) * intensity);
        const x = i * (bw + gap);
        const y = mid - bh / 2;
        // Solid fill; quieter bars read slightly lighter for subtle depth.
        cx!.globalAlpha = 0.45 + Math.min(0.55, norm * 0.6);
        const r = Math.min(bw / 2, 3);
        roundRect(cx!, x, y, bw, bh, r);
        cx!.fill();
      }
      cx!.globalAlpha = 1;

      if (!reduced) raf = requestAnimationFrame(draw);
    }

    if (reduced) {
      draw(1200);
    } else {
      raf = requestAnimationFrame(draw);
    }

    return () => {
      running = false;
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, [bars, height, intensity]);

  return (
    <canvas
      ref={canvasRef}
      className={className}
      role="img"
      aria-label="Live voice waveform"
      style={{ width: "100%", height }}
    />
  );
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number
) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}
