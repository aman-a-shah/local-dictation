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
