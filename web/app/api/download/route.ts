import { NextRequest, NextResponse } from "next/server";
import { track } from "@vercel/analytics/server";
import { BUILDS, latestAssetUrl, resolveBuild, type BuildKey } from "@/lib/releases";

export const runtime = "edge";

/**
 * GET /api/download?os=mac&arch=arm64
 * 302-redirects to the correct latest GitHub Release asset. Unknown combos fall
 * back to the download page so the visitor can choose.
 *
 * Every real download button funnels through here, so this is also where we
 * count downloads: a server-side "download" event fires before the redirect,
 * which catches every platform and isn't affected by client-side ad-blockers.
 * Tracking is best-effort — a failure here must never block the download.
 */
export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const key = resolveBuild(searchParams.get("os"), searchParams.get("arch"));
  if (!key) {
    return NextResponse.redirect(new URL("/download", req.url), 302);
  }
  const build = BUILDS[key];
  await Promise.all([
    track("download", {
      build: key,
      os: build.platform,
      arch: build.arch,
    }).catch(() => {}),
    trackGa(req, key, build).catch(() => {}),
  ]);
  return NextResponse.redirect(latestAssetUrl(build.asset), 302);
}

/**
 * Mirror the download into GA4 via the Measurement Protocol so the same
 * ad-blocker-proof, every-platform count shows up next to the page-view data in
 * Google Analytics. No-ops unless both the public Measurement ID and the
 * server-only API secret are set, so dev/preview without secrets stay quiet.
 */
async function trackGa(
  req: NextRequest,
  key: BuildKey,
  build: (typeof BUILDS)[BuildKey],
): Promise<void> {
  const measurementId = process.env.NEXT_PUBLIC_GA_ID;
  const apiSecret = process.env.GA_API_SECRET;
  if (!measurementId || !apiSecret) return;

  const url =
    `https://www.google-analytics.com/mp/collect?measurement_id=${measurementId}` +
    `&api_secret=${apiSecret}`;

  await fetch(url, {
    method: "POST",
    body: JSON.stringify({
      client_id: gaClientId(req),
      events: [
        {
          name: "download",
          params: {
            build: key,
            os: build.platform,
            arch: build.arch,
          },
        },
      ],
    }),
  });
}

/**
 * Reuse the visitor's gtag.js client id (stored in the `_ga` cookie as
 * `GA1.1.<id>.<ts>`) so a server-side download stitches to the same session as
 * their page views. Falls back to a fresh random id when the cookie is absent.
 */
function gaClientId(req: NextRequest): string {
  const ga = req.cookies.get("_ga")?.value;
  const m = ga?.match(/^GA\d+\.\d+\.(\d+\.\d+)$/);
  return m ? m[1] : crypto.randomUUID();
}
