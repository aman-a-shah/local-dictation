"use client";

import { useRef, type ReactNode } from "react";

/**
 * Subtle 3D tilt toward the cursor (premium "this is a real object" feel).
 * Pointer-driven only, disabled under reduced motion, and never traps clicks.
 */
export function Tilt({
  children,
  max = 6,
  className,
}: {
  children: ReactNode;
  max?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);

  const onMove = (e: React.MouseEvent) => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const r = el.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width - 0.5;
    const py = (e.clientY - r.top) / r.height - 0.5;
    el.style.transform = `perspective(1100px) rotateX(${(-py * max).toFixed(2)}deg) rotateY(${(px * max).toFixed(2)}deg)`;
  };
  const reset = () => {
    const el = ref.current;
    if (el) el.style.transform = "perspective(1100px) rotateX(0deg) rotateY(0deg)";
  };

  return (
    <div
      ref={ref}
      className={className}
      onMouseMove={onMove}
      onMouseLeave={reset}
      style={{ transition: "transform 300ms cubic-bezier(0.16,1,0.3,1)", willChange: "transform" }}
    >
      {children}
    </div>
  );
}
