import { NextResponse } from "next/server";

import { BackendRequestError } from "@/lib/backend/client";

type ErrorPayload = Record<string, unknown>;

export function backendErrorResponse(
  error: unknown,
  fallbackMessage: string,
): NextResponse<ErrorPayload> {
  if (error instanceof BackendRequestError) {
    return NextResponse.json(toErrorPayload(error.payload, fallbackMessage), {
      status: error.status,
    });
  }
  return NextResponse.json({ message: fallbackMessage }, { status: 502 });
}

function toErrorPayload(payload: unknown, fallbackMessage: string): ErrorPayload {
  if (payload !== null && typeof payload === "object" && !Array.isArray(payload)) {
    return payload as ErrorPayload;
  }
  return { message: fallbackMessage };
}
