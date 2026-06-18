import { NextRequest, NextResponse } from "next/server";
import { BUILDS, latestAssetUrl, resolveBuild } from "@/lib/releases";

export const runtime = "edge";

/**
 * GET /api/download?os=mac&arch=arm64
 * 302-redirects to the correct latest GitHub Release asset. Unknown combos fall
 * back to the download page so the visitor can choose.
 */
export function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const key = resolveBuild(searchParams.get("os"), searchParams.get("arch"));
  if (!key) {
    return NextResponse.redirect(new URL("/download", req.url), 302);
  }
  return NextResponse.redirect(latestAssetUrl(BUILDS[key].asset), 302);
}
