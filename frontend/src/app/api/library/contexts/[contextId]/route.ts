import { NextResponse } from "next/server";

import { loadContextFromBackend } from "@/lib/backend/contexts";
import { backendErrorResponse } from "@/lib/backend/route-errors";

type ContextRouteProps = {
  params: Promise<{ contextId: string }>;
};

export async function GET(_request: Request, { params }: ContextRouteProps) {
  try {
    const { contextId } = await params;
    return NextResponse.json(
      await loadContextFromBackend(decodeURIComponent(contextId)),
    );
  } catch (error) {
    return backendErrorResponse(error, "Context load failed");
  }
}
