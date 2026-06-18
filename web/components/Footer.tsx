import Link from "next/link";
import { Logo } from "@local-dictation/ui";
import { REPO } from "@/lib/releases";
import styles from "./Footer.module.css";

export function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.inner}>
        <div className={styles.brand}>
          <Logo size={24} />
          <p className={styles.tagline}>
            Voice typing that stays on your machine. Your words never leave the
            device.
          </p>
        </div>
        <nav className={styles.col} aria-label="Product">
          <h3>Product</h3>
          <Link href="/download">Download</Link>
          <Link href="/#how">How it works</Link>
          <Link href="/faq">FAQ</Link>
          <Link href="/changelog">Changelog</Link>
        </nav>
        <nav className={styles.col} aria-label="Legal">
          <h3>Legal</h3>
          <Link href="/privacy">Privacy</Link>
          <Link href="/terms">Terms</Link>
          <a href={`https://github.com/${REPO}/blob/main/SECURITY.md`}>Security</a>
        </nav>
        <nav className={styles.col} aria-label="Open source">
          <h3>Open source</h3>
          <a href={`https://github.com/${REPO}`}>GitHub</a>
          <a href={`https://github.com/${REPO}/blob/main/ACKNOWLEDGEMENTS.md`}>
            Acknowledgements
          </a>
        </nav>
      </div>
      <div className={styles.bottom}>
        <span>© {new Date().getFullYear()} Local Dictation</span>
        <span className={styles.mono}>Runs 100% on-device · No telemetry</span>
      </div>
    </footer>
  );
}
