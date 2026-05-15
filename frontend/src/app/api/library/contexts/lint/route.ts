import { NextResponse } from "next/server";

import { lintContextInBackend } from "@/lib/backend/contexts";
import { backendErrorResponse } from "@/lib/backend/route-errors";
import type { ContextLintRequestDTO } from "@/types/library";

export async function POST(request: Request) {
  try {
    const payload = (await request.json()) as ContextLintRequestDTO;
    return NextResponse.json(await lintContextInBackend(payload));
  } catch (error) {
    return backendErrorResponse(error, "Context lint failed");
  }
}
