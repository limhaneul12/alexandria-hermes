import { NextResponse } from "next/server";

import { testLibrarianProviderInBackend } from "@/lib/backend/librarians";
import { backendFailureResponse } from "../../../_shared/backend-error-response";
import { routeErrorPayload } from "@/lib/backend/route-errors";
import { isRecord } from "../../../_shared/request-parsing";

export async function POST(
  request: Request,
  context: { params: Promise<{ providerId: string }> },
) {
  const { providerId } = await context.params;
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(routeErrorPayload("INVALID_LIBRARIAN_PROVIDER_TEST_PAYLOAD", "Invalid librarian provider test payload."), { status: 400 });
  }
  if (!isRecord(body)) {
    return NextResponse.json(routeErrorPayload("INVALID_LIBRARIAN_PROVIDER_TEST_PAYLOAD", "Invalid librarian provider test payload."), { status: 400 });
  }
  const testQuery = typeof body.testQuery === "string" && body.testQuery.trim()
    ? body.testQuery.trim()
    : "ping";

  try {
    return NextResponse.json(await testLibrarianProviderInBackend(providerId, testQuery));
  } catch (error) {
    return backendFailureResponse(error, "Librarian provider test failed", "LIBRARIAN_PROVIDER_TEST_FAILED");
  }
}
