import { NextResponse } from "next/server";

import { loadContextsFromBackend } from "@/lib/backend/contexts";
import { backendErrorResponse } from "@/lib/backend/route-errors";

export async function GET(request: Request) {
  try {
    return NextResponse.json(
      await loadContextsFromBackend(new URL(request.url).searchParams),
    );
  } catch (error) {
    return backendErrorResponse(error, "Context list failed");
  }
}
