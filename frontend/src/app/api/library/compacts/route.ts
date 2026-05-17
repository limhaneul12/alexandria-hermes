import { NextResponse } from "next/server";

import { loadMemoryCompactsFromBackend } from "@/lib/backend/memory-compacts";
import { backendErrorResponse } from "@/lib/backend/route-errors";

export async function GET(request: Request) {
  try {
    return NextResponse.json(
      await loadMemoryCompactsFromBackend(new URL(request.url).searchParams),
    );
  } catch (error) {
    return backendErrorResponse(error, "Memory Compact list failed");
  }
}
