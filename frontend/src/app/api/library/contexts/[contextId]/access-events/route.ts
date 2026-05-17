import { NextResponse } from "next/server";

import {
  loadContextAccessEventsFromBackend,
  recordContextAccessEventInBackend,
} from "@/lib/backend/contexts";
import { backendErrorResponse } from "@/lib/backend/route-errors";
import type { ContextAccessEventCreateDTO } from "@/types/library";

type ContextRouteProps = {
  params: Promise<{ contextId: string }>;
};

export async function GET(request: Request, { params }: ContextRouteProps) {
  try {
    const { contextId } = await params;
    const limit = Number(new URL(request.url).searchParams.get("limit") ?? 5);
    return NextResponse.json(
      await loadContextAccessEventsFromBackend(decodeURIComponent(contextId), limit),
    );
  } catch (error) {
    return backendErrorResponse(error, "Context access events failed");
  }
}

export async function POST(request: Request, { params }: ContextRouteProps) {
  try {
    const { contextId } = await params;
    const payload = (await request.json()) as ContextAccessEventCreateDTO;
    return NextResponse.json(
      await recordContextAccessEventInBackend(decodeURIComponent(contextId), payload),
      { status: 201 },
    );
  } catch (error) {
    return backendErrorResponse(error, "Context access event record failed");
  }
}
