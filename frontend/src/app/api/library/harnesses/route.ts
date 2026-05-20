import { NextResponse } from "next/server";

import {
  captureHarnessInBackend,
  loadHarnessesFromBackend,
} from "@/lib/backend/harnesses";
import { backendErrorResponse, routeErrorPayload } from "@/lib/backend/route-errors";
import { parseHarnessCaptureBody } from "./harness-route-payload";

export async function GET(request: Request) {
  try {
    return NextResponse.json(
      await loadHarnessesFromBackend(new URL(request.url).searchParams),
    );
  } catch (error) {
    return backendErrorResponse(error, "Harness list failed");
  }
}

export async function POST(request: Request) {
  let rawBody: unknown;
  try {
    rawBody = await request.json();
  } catch {
    return NextResponse.json(routeErrorPayload("INVALID_HARNESS_PAYLOAD", "Invalid harness payload."), { status: 400 });
  }
  const parsed = parseHarnessCaptureBody(rawBody);
  if (!parsed.ok) {
    return NextResponse.json(routeErrorPayload(parsed.code, parsed.message), { status: 400 });
  }
  try {
    return NextResponse.json(await captureHarnessInBackend(parsed.payload), { status: 201 });
  } catch (error) {
    return backendErrorResponse(error, "Harness capture failed");
  }
}
