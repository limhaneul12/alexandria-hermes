import { NextResponse } from "next/server";

import { checkHarnessInBackend } from "@/lib/backend/harnesses";
import { backendErrorResponse, routeErrorPayload } from "@/lib/backend/route-errors";
import { parseHarnessCaptureBody } from "../harness-route-payload";

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
    return NextResponse.json(await checkHarnessInBackend(parsed.payload));
  } catch (error) {
    return backendErrorResponse(error, "Harness check failed");
  }
}
