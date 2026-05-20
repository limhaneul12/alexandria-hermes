import { NextResponse } from "next/server";

import { BackendRequestError } from "@/lib/backend/client";
import { routeErrorPayload } from "@/lib/backend/route-errors";

export function backendFailureResponse(
  error: unknown,
  fallbackMessage: string,
  fallbackCode = "BACKEND_REQUEST_FAILED",
) {
  if (error instanceof BackendRequestError) {
    return NextResponse.json(
      error.payload ?? routeErrorPayload(fallbackCode, fallbackMessage),
      { status: error.status },
    );
  }
  return NextResponse.json(routeErrorPayload(fallbackCode, fallbackMessage), {
    status: 502,
  });
}
