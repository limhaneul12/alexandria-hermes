import { NextResponse } from "next/server";

import { loadContextsFromBackend, saveContextInBackend } from "@/lib/backend/contexts";
import { backendErrorResponse } from "@/lib/backend/route-errors";
import type { ContextSaveDTO } from "@/types/library";

export async function GET(request: Request) {
  try {
    return NextResponse.json(
      await loadContextsFromBackend(new URL(request.url).searchParams),
    );
  } catch (error) {
    return backendErrorResponse(error, "Context list failed");
  }
}

export async function POST(request: Request) {
  try {
    const payload = (await request.json()) as ContextSaveDTO;
    return NextResponse.json(await saveContextInBackend(payload), { status: 201 });
  } catch (error) {
    return backendErrorResponse(error, "Context save failed");
  }
}
