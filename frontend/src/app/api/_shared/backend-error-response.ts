import { NextResponse } from "next/server";

import { BackendRequestError } from "@/lib/backend/client";

export function backendFailureResponse(error: unknown, fallbackMessage: string) {
  if (error instanceof BackendRequestError) {
    return NextResponse.json(error.payload ?? { message: fallbackMessage }, { status: error.status });
  }
  return NextResponse.json({ message: fallbackMessage }, { status: 502 });
}
