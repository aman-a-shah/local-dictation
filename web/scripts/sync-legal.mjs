// Copies the canonical legal markdown (repo /legal) into web/content so the site
// renders the exact same documents shipped with the app — single source of truth,
// no drift. Runs in predev/prebuild. Safe if files are missing (warns).
import { mkdirSync, copyFileSync, existsSync, readdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(here, "..");
const candidates = [resolve(webRoot, "../legal"), resolve(webRoot, "../../legal")];
const src = candidates.find((p) => existsSync(p));
const dest = join(webRoot, "content");

mkdirSync(dest, { recursive: true });

if (!src) {
  console.warn("[sync-legal] no /legal dir found; skipping (pages will show a fallback).");
  process.exit(0);
}

let n = 0;
for (const f of readdirSync(src)) {
  if (f.endsWith(".md")) {
    copyFileSync(join(src, f), join(dest, f));
    n++;
  }
}
console.log(`[sync-legal] copied ${n} legal doc(s) from ${src} -> ${dest}`);
