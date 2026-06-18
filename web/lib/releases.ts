/**
 * Single source of truth for downloads + updates.
 *
 * Binaries are published as GitHub Release assets by .github/workflows/release.yml
 * with stable names, so `releases/latest/download/<asset>` always resolves to the
 * newest build. The API routes and the download page both import from here.
 */

export const REPO = process.env.NEXT_PUBLIC_GH_REPO || "aman-a-shah/local-transcription";

/** Fallback version shown before the GitHub API responds (keep in sync with dictate/__init__.py). */
export const FALLBACK_VERSION = "1.0.0";

export type Platform = "mac" | "windows" | "linux";
export type Arch = "arm64" | "x64";

export type BuildKey = "mac-arm64" | "mac-x64" | "windows-x64";

export const BUILDS: Record<
  BuildKey,
  { label: string; sublabel: string; platform: Platform; arch: Arch; asset: string; ext: string }
> = {
  "mac-arm64": {
    label: "macOS — Apple Silicon",
    sublabel: "M1, M2, M3, M4",
    platform: "mac",
    arch: "arm64",
    asset: "LocalDictation-mac-arm64.dmg",
    ext: ".dmg",
  },
  "mac-x64": {
    label: "macOS — Intel",
    sublabel: "2020 & earlier Macs",
    platform: "mac",
    arch: "x64",
    asset: "LocalDictation-mac-x64.dmg",
    ext: ".dmg",
  },
  "windows-x64": {
    label: "Windows",
    sublabel: "Windows 10 & 11, 64-bit",
    platform: "windows",
    arch: "x64",
    asset: "LocalDictationSetup-windows-x64.exe",
    ext: ".exe",
  },
};

export function latestAssetUrl(asset: string): string {
  return `https://github.com/${REPO}/releases/latest/download/${asset}`;
}

/** Map an OS/arch query to a build key. */
export function resolveBuild(os?: string | null, arch?: string | null): BuildKey | null {
  const o = (os || "").toLowerCase();
  const a = (arch || "").toLowerCase();
  if (o === "mac" || o === "macos" || o === "darwin") {
    return a === "arm64" || a === "aarch64" ? "mac-arm64" : "mac-x64";
  }
  if (o === "windows" || o === "win") return "windows-x64";
  return null;
}

export type ReleaseInfo = {
  version: string;
  notes: string;
  publishedAt: string | null;
  htmlUrl: string;
};

/**
 * Fetch the latest published release from GitHub (cached). Falls back to a static
 * version so the site/endpoints never hard-fail if the API is unreachable.
 */
export async function getLatestRelease(): Promise<ReleaseInfo> {
  try {
    const res = await fetch(`https://api.github.com/repos/${REPO}/releases/latest`, {
      headers: { Accept: "application/vnd.github+json" },
      next: { revalidate: 1800 },
    });
    if (!res.ok) throw new Error(`GitHub ${res.status}`);
    const data = await res.json();
    return {
      version: String(data.tag_name || FALLBACK_VERSION).replace(/^v/, ""),
      notes: String(data.body || ""),
      publishedAt: data.published_at ?? null,
      htmlUrl: data.html_url ?? `https://github.com/${REPO}/releases`,
    };
  } catch {
    return {
      version: FALLBACK_VERSION,
      notes: "",
      publishedAt: null,
      htmlUrl: `https://github.com/${REPO}/releases`,
    };
  }
}
