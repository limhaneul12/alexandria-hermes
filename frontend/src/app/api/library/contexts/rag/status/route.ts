import { NextResponse } from "next/server";

import { loadRagStatusFromBackend } from "@/lib/backend/contexts";
import { backendErrorResponse } from "@/lib/backend/route-errors";

export async function GET() {
  try {
    return NextResponse.json(await loadRagStatusFromBackend());
  } catch (error) {
    return backendErrorResponse(error, "RAG status failed");
  }
}
