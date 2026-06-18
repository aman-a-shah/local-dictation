import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { marked } from "marked";
import { REPO } from "./releases";

/** Render a legal markdown doc (synced into web/content) to HTML. */
export function renderLegal(slug: "privacy" | "terms"): { html: string; missing: boolean } {
  const path = join(process.cwd(), "content", `${slug}.md`);
  if (!existsSync(path)) {
    return {
      missing: true,
      html: `<p>This document lives in the repository. Read it on <a href="https://github.com/${REPO}/blob/main/legal/${slug}.md">GitHub</a>.</p>`,
    };
  }
  let md = readFileSync(path, "utf-8");
  // Fill the most common placeholders so the rendered page reads cleanly even
  // before the owner sets real values (kept obvious, not fake).
  md = md.replace(/\[your-repo-url\]/g, `https://github.com/${REPO}`);
  const html = marked.parse(md, { async: false }) as string;
  return { html, missing: false };
}
