import { NextResponse } from "next/server";

import { loadLibraryFromBackend } from "@/lib/backend/archive";

export async function GET(request: Request) {
  return NextResponse.json(await loadLibraryFromBackend(new URL(request.url).searchParams));
}
