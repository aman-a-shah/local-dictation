import { NextRequest, NextResponse } from "next/server";
import { BUILDS, latestAssetUrl, getLatestRelease, resolveBuild } from "@/lib/releases";

export const revalidate = 1800;

/**
 * GET /api/update?platform=mac&arch=arm64&version=1.0.0
 * The app polls this. Returns the latest version + the correct installer URL for
 * that platform/arch. The app does the version comparison client-side.
 */
export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const platform = searchParams.get("platform");
  const arch = searchParams.get("arch");
  const release = await getLatestRelease();

  const key = resolveBuild(platform, arch);
  const url = key ? latestAssetUrl(BUILDS[key].asset) : null;

  return NextResponse.json(
    {
      version: release.version,
      url,
      notes: release.notes,
      publishedAt: release.publishedAt,
    },
    { headers: { "Cache-Control": "public, max-age=900, s-maxage=1800" } }
  );
}
