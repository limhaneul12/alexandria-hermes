import { NextResponse } from "next/server";

import { loadHarnessesFromBackend } from "@/lib/backend/harnesses";
import { backendErrorResponse } from "@/lib/backend/route-errors";

export async function GET(request: Request) {
  try {
    return NextResponse.json(
      await loadHarnessesFromBackend(new URL(request.url).searchParams),
    );
  } catch (error) {
    return backendErrorResponse(error, "Harness list failed");
  }
}
