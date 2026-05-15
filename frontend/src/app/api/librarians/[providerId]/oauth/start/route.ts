import { NextResponse } from "next/server";

import { startLibrarianOAuthInBackend } from "@/lib/backend/librarians";
import { backendFailureResponse } from "../../../../_shared/backend-error-response";

export async function POST(
  _request: Request,
  context: { params: Promise<{ providerId: string }> },
) {
  const { providerId } = await context.params;
  try {
    return NextResponse.json(await startLibrarianOAuthInBackend(providerId));
  } catch (error) {
    return backendFailureResponse(error, "OAuth authorization could not be started.");
  }
}
