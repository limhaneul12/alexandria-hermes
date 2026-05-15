import { NextResponse } from "next/server";

import { accessContextInBackend } from "@/lib/backend/contexts";
import { backendErrorResponse } from "@/lib/backend/route-errors";

type ContextRouteProps = {
  params: Promise<{ contextId: string }>;
};

export async function POST(_request: Request, { params }: ContextRouteProps) {
  try {
    const { contextId } = await params;
    return NextResponse.json(
      await accessContextInBackend(decodeURIComponent(contextId)),
    );
  } catch (error) {
    return backendErrorResponse(error, "Context access failed");
  }
}
