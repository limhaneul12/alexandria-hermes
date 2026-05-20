import { NextResponse } from "next/server";

import { archiveMemoryCompactInBackend } from "@/lib/backend/memory-compacts";
import { backendErrorResponse } from "@/lib/backend/route-errors";

type MemoryCompactArchiveRouteProps = {
  params: Promise<{ compactId: string }>;
};

export async function POST(
  _request: Request,
  { params }: MemoryCompactArchiveRouteProps,
) {
  try {
    const { compactId } = await params;
    return NextResponse.json(
      await archiveMemoryCompactInBackend(decodeURIComponent(compactId)),
    );
  } catch (error) {
    return backendErrorResponse(error, "Memory Compact archive failed");
  }
}
