import { NextResponse } from "next/server";

import { searchContextsInBackend } from "@/lib/backend/contexts";
import { backendErrorResponse } from "@/lib/backend/route-errors";
import type { ContextSearchDTO } from "@/types/library";

export async function POST(request: Request) {
  try {
    const payload = (await request.json()) as ContextSearchDTO;
    return NextResponse.json(await searchContextsInBackend(payload));
  } catch (error) {
    return backendErrorResponse(error, "Context search failed");
  }
}
