import { NextResponse } from "next/server";

import { archiveContextInBackend } from "@/lib/backend/contexts";
import { backendErrorResponse } from "@/lib/backend/route-errors";

type ContextRouteProps = {
  params: Promise<{ contextId: string }>;
};

export async function POST(_request: Request, { params }: ContextRouteProps) {
  try {
    const { contextId } = await params;
    return NextResponse.json(
      await archiveContextInBackend(decodeURIComponent(contextId)),
    );
  } catch (error) {
    return backendErrorResponse(error, "Context archive failed");
  }
}
