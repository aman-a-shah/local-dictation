"use client";

import Link from "next/link";
import { Logo, ButtonLink, useScrollProgress } from "@voca/ui";
import styles from "./Nav.module.css";

export function Nav() {
  const progress = useScrollProgress();
  return (
    <header className={styles.nav}>
      <div className={styles.inner}>
        <Link href="/" aria-label="Voca home" className={styles.brand}>
          <Logo size={26} />
        </Link>
        <nav className={styles.links} aria-label="Primary">
          <Link href="/#how">How it works</Link>
          <Link href="/#privacy">Privacy</Link>
          <Link href="/faq">FAQ</Link>
          <Link href="/changelog">Changelog</Link>
        </nav>
        <ButtonLink href="/download" className={styles.cta}>
          Download
        </ButtonLink>
      </div>
      <div
        className={styles.progress}
        style={{ ["--p" as string]: `${(progress * 100).toFixed(2)}%` }}
        aria-hidden="true"
      />
    </header>
  );
}
