import { NextResponse } from "next/server";

import { prepareCompactInBackend } from "@/lib/backend/contexts";
import { backendErrorResponse } from "@/lib/backend/route-errors";
import type { ContextPrepareCompactDTO } from "@/types/library";

export async function POST(request: Request) {
  try {
    const payload = (await request.json()) as ContextPrepareCompactDTO;
    return NextResponse.json(await prepareCompactInBackend(payload), { status: 201 });
  } catch (error) {
    return backendErrorResponse(error, "Compact preparation failed");
  }
}
