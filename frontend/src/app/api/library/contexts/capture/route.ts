import { NextResponse } from "next/server";

import { captureContextInBackend } from "@/lib/backend/contexts";
import { backendErrorResponse } from "@/lib/backend/route-errors";
import type { ContextSaveDTO } from "@/types/library";

export async function POST(request: Request) {
  try {
    const payload = (await request.json()) as ContextSaveDTO;
    return NextResponse.json(await captureContextInBackend(payload), { status: 201 });
  } catch (error) {
    return backendErrorResponse(error, "Context capture failed");
  }
}
