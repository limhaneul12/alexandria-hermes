import { NextResponse } from "next/server";

import { loadCurrentMemoryCompactFromBackend } from "@/lib/backend/memory-compacts";
import { backendErrorResponse } from "@/lib/backend/route-errors";

export async function GET(request: Request) {
  try {
    const project = new URL(request.url).searchParams.get("project");
    return NextResponse.json(await loadCurrentMemoryCompactFromBackend(project));
  } catch (error) {
    return backendErrorResponse(error, "Current Memory Compact load failed");
  }
}
