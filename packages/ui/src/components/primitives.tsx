import type { ButtonHTMLAttributes, AnchorHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "ghost";

function btnClass(variant: Variant, size?: "lg", block?: boolean, extra?: string) {
  return [
    "ld-btn",
    `ld-btn--${variant}`,
    size === "lg" ? "ld-btn--lg" : "",
    block ? "ld-btn--block" : "",
    extra ?? "",
  ]
    .filter(Boolean)
    .join(" ");
}

export function Button({
  variant = "primary",
  size,
  block,
  className,
  ...rest
}: { variant?: Variant; size?: "lg"; block?: boolean } & ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={btnClass(variant, size, block, className)} {...rest} />;
}

export function ButtonLink({
  variant = "primary",
  size,
  block,
  className,
  ...rest
}: { variant?: Variant; size?: "lg"; block?: boolean } & AnchorHTMLAttributes<HTMLAnchorElement>) {
  return <a className={btnClass(variant, size, block, className)} {...rest} />;
}

export function Kbd({ children }: { children: ReactNode }) {
  return <kbd className="ld-kbd">{children}</kbd>;
}

export function Tag({ children }: { children: ReactNode }) {
  return (
    <span className="ld-tag">
      <span className="ld-tag__dot" aria-hidden="true" />
      {children}
    </span>
  );
}

export function Stat({
  value,
  label,
  size = "clamp(2rem, 1.4rem + 2.4vw, 3rem)",
}: {
  value: ReactNode;
  label: ReactNode;
  size?: string;
}) {
  return (
    <div>
      <div className="ld-stat__num" style={{ fontSize: size }}>
        {value}
      </div>
      <div className="ld-stat__label">{label}</div>
    </div>
  );
}
