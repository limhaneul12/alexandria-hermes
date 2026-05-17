import { NextResponse } from "next/server";

import { loadMemoryCompactFromBackend } from "@/lib/backend/memory-compacts";
import { backendErrorResponse } from "@/lib/backend/route-errors";

type MemoryCompactRouteProps = {
  params: Promise<{ compactId: string }>;
};

export async function GET(_request: Request, { params }: MemoryCompactRouteProps) {
  try {
    const { compactId } = await params;
    return NextResponse.json(
      await loadMemoryCompactFromBackend(decodeURIComponent(compactId)),
    );
  } catch (error) {
    return backendErrorResponse(error, "Memory Compact load failed");
  }
}
