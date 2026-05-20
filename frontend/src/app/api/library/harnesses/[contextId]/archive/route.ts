import { NextResponse } from "next/server";

import { archiveHarnessInBackend } from "@/lib/backend/harnesses";
import { backendErrorResponse } from "@/lib/backend/route-errors";

type HarnessRouteProps = {
  params: Promise<{ contextId: string }>;
};

export async function POST(_request: Request, { params }: HarnessRouteProps) {
  try {
    const { contextId } = await params;
    return NextResponse.json(await archiveHarnessInBackend(decodeURIComponent(contextId)));
  } catch (error) {
    return backendErrorResponse(error, "Harness archive failed");
  }
}
