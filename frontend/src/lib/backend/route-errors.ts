import { NextResponse } from "next/server";

import { BackendRequestError } from "@/lib/backend/client";

export type RouteErrorPayload = {
  code: string;
  message: string;
};

type ErrorPayload = RouteErrorPayload & Record<string, unknown>;

export function routeErrorPayload(code: string, message: string): RouteErrorPayload {
  return { code, message };
}

export function backendErrorResponse(
  error: unknown,
  fallbackMessage: string,
  fallbackCode = "BACKEND_REQUEST_FAILED",
): NextResponse<ErrorPayload> {
  if (error instanceof BackendRequestError) {
    return NextResponse.json(
      toErrorPayload(error.payload, fallbackCode, fallbackMessage),
      { status: error.status },
    );
  }
  return NextResponse.json(routeErrorPayload(fallbackCode, fallbackMessage), {
    status: 502,
  });
}

function toErrorPayload(
  payload: unknown,
  fallbackCode: string,
  fallbackMessage: string,
): ErrorPayload {
  if (payload !== null && typeof payload === "object" && !Array.isArray(payload)) {
    const record = payload as Record<string, unknown>;
    return {
      ...record,
      code: typeof record.code === "string" ? record.code : fallbackCode,
      message: typeof record.message === "string" ? record.message : fallbackMessage,
    };
  }
  return routeErrorPayload(fallbackCode, fallbackMessage);
}
