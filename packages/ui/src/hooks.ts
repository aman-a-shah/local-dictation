"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Adds `.is-in` to elements with `.ld-reveal` as they enter the viewport. The
 * default state is fully visible (see components.css) — the class only *enhances*
 * with motion when motion is allowed, so content never ships blank.
 */
export function useReveal<T extends HTMLElement = HTMLElement>() {
  const ref = useRef<T>(null);
  useEffect(() => {
    const root = ref.current;
    if (!root) return;
    const els = Array.from(root.querySelectorAll<HTMLElement>(".ld-reveal"));
    if (!("IntersectionObserver" in window) || els.length === 0) {
      els.forEach((el) => el.classList.add("is-in"));
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            e.target.classList.add("is-in");
            io.unobserve(e.target);
          }
        }
      },
      { rootMargin: "0px 0px -10% 0px", threshold: 0.1 }
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);
  return ref;
}

/** True once the element has scrolled into view (fires once). */
export function useInView<T extends HTMLElement = HTMLElement>(rootMargin = "0px 0px -15% 0px") {
  const ref = useRef<T>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (!("IntersectionObserver" in window)) {
      setInView(true);
      return;
    }
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setInView(true);
          io.disconnect();
        }
      },
      { rootMargin, threshold: 0.2 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [rootMargin]);
  return { ref, inView };
}

/** Animate a number from 0 → end with an ease-out curve once `active`. */
export function useCountUp(end: number, active: boolean, durationMs = 1400) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (!active) return;
    const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      setValue(end);
      return;
    }
    let raf = 0;
    let start = 0;
    const step = (t: number) => {
      if (!start) start = t;
      const p = Math.min(1, (t - start) / durationMs);
      const eased = 1 - Math.pow(1 - p, 4); // ease-out-quart
      setValue(end * eased);
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [end, active, durationMs]);
  return value;
}

/** 0..1 scroll progress of the whole document (for a nav progress bar). */
export function useScrollProgress() {
  const [progress, setProgress] = useState(0);
  useEffect(() => {
    const onScroll = () => {
      const h = document.documentElement;
      const max = h.scrollHeight - h.clientHeight;
      setProgress(max > 0 ? h.scrollTop / max : 0);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  return progress;
}

export type DetectedOS = "mac-arm64" | "mac-x64" | "windows" | "linux" | "unknown";

/** Best-effort OS + arch detection for the download page (UA + hints). */
export function detectOS(): DetectedOS {
  if (typeof navigator === "undefined") return "unknown";
  const ua = navigator.userAgent;
  const platform = (navigator as any).userAgentData?.platform || navigator.platform || "";
  const isMac = /Mac/i.test(ua) || /Mac/i.test(platform);
  const isWin = /Win/i.test(ua) || /Win/i.test(platform);
  if (isWin) return "windows";
  if (isMac) {
    // Apple Silicon is hard to detect directly; WebGL renderer is the best hint.
    if (isAppleSilicon()) return "mac-arm64";
    return "mac-x64";
  }
  if (/Linux|X11/i.test(ua)) return "linux";
  return "unknown";
}

function isAppleSilicon(): boolean {
  try {
    const canvas = document.createElement("canvas");
    const gl = canvas.getContext("webgl") as WebGLRenderingContext | null;
    if (!gl) return true; // modern Macs are mostly Apple Silicon; default to arm64
    const dbg = gl.getExtension("WEBGL_debug_renderer_info");
    const renderer = dbg ? (gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) as string) : "";
    // Intel Macs report an "Intel" GPU; Apple Silicon reports "Apple".
    if (/Apple/i.test(renderer)) return true;
    if (/Intel|AMD|Radeon/i.test(renderer)) return false;
    return true;
  } catch {
    return true;
  }
}

export function useDetectedOS(): DetectedOS {
  const [os, setOS] = useState<DetectedOS>("unknown");
  useEffect(() => setOS(detectOS()), []);
  return os;
}
