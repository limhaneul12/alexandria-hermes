import { NextResponse } from "next/server";

import { loadLibrarianOAuthStatusFromBackend } from "@/lib/backend/librarians";
import { backendFailureResponse } from "../../../../_shared/backend-error-response";

export async function GET(
  _request: Request,
  context: { params: Promise<{ providerId: string }> },
) {
  const { providerId } = await context.params;
  try {
    return NextResponse.json(await loadLibrarianOAuthStatusFromBackend(providerId));
  } catch (error) {
    return backendFailureResponse(
      error,
      "OAuth authorization status could not be loaded.",
    );
  }
}
