"use client";

import { useInView, useCountUp } from "../hooks";

type Props = {
  /** The numeric target. */
  end: number;
  /** Decimal places to show. */
  decimals?: number;
  prefix?: string;
  suffix?: string;
  /** Use compact grouping (e.g. 8,690). */
  group?: boolean;
  className?: string;
};

/** A number that counts up from 0 the first time it scrolls into view. */
export function CountUp({ end, decimals = 0, prefix = "", suffix = "", group = true, className }: Props) {
  const { ref, inView } = useInView<HTMLSpanElement>();
  const value = useCountUp(end, inView);
  const rounded = Number(value.toFixed(decimals));
  const text = group
    ? rounded.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
    : rounded.toFixed(decimals);
  return (
    <span ref={ref} className={className}>
      {prefix}
      {text}
      {suffix}
    </span>
  );
}
