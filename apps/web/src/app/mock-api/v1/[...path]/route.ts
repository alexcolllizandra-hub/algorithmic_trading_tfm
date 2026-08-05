import { NextResponse } from "next/server";

import { resolveFixture } from "@/mock/fixtures";

// Mock API used ONLY for standalone frontend runs and Playwright E2E, activated
// by pointing NEXT_PUBLIC_API_BASE at /mock-api/v1. It serves clearly-labelled
// synthetic fixtures and never touches real artifacts.
export const dynamic = "force-dynamic";

export async function GET(
  req: Request,
  { params }: { params: { path: string[] } }
): Promise<NextResponse> {
  const pathname = "/" + (params.path?.join("/") ?? "");
  const url = new URL(req.url);
  const data = resolveFixture(pathname, url.searchParams);
  if (data === null) {
    return NextResponse.json({ detail: `mock: no fixture for ${pathname}` }, { status: 404 });
  }
  return NextResponse.json(data);
}
