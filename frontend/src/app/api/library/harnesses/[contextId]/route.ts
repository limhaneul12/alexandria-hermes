import { NextResponse } from "next/server";

import { loadHarnessFromBackend } from "@/lib/backend/harnesses";
import { backendErrorResponse } from "@/lib/backend/route-errors";

type HarnessRouteProps = {
  params: Promise<{ contextId: string }>;
};

export async function GET(_request: Request, { params }: HarnessRouteProps) {
  try {
    const { contextId } = await params;
    return NextResponse.json(await loadHarnessFromBackend(decodeURIComponent(contextId)));
  } catch (error) {
    return backendErrorResponse(error, "Harness load failed");
  }
}
