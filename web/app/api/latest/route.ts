import { NextResponse } from "next/server";
import { BUILDS, latestAssetUrl, getLatestRelease } from "@/lib/releases";

export const revalidate = 1800;

/** GET /api/latest — version metadata + all build URLs (for the download page). */
export async function GET() {
  const release = await getLatestRelease();
  const builds = Object.fromEntries(
    Object.entries(BUILDS).map(([key, b]) => [
      key,
      { label: b.label, url: latestAssetUrl(b.asset), asset: b.asset },
    ])
  );
  return NextResponse.json({ ...release, builds });
}
