"use client";

import { useReveal } from "@local-dictation/ui";

/** Wraps content; children with the `ld-reveal` class animate in on scroll. */
export function Reveal({ children }: { children: React.ReactNode }) {
  const ref = useReveal<HTMLDivElement>();
  return <div ref={ref}>{children}</div>;
}
