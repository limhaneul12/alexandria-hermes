import { NextResponse } from "next/server";

import { refreshLibrarianOAuthInBackend } from "@/lib/backend/librarians";
import { backendFailureResponse } from "../../../../_shared/backend-error-response";

export async function POST(
  _request: Request,
  context: { params: Promise<{ providerId: string }> },
) {
  const { providerId } = await context.params;
  try {
    return NextResponse.json(await refreshLibrarianOAuthInBackend(providerId));
  } catch (error) {
    return backendFailureResponse(error, "OAuth authorization could not be refreshed.");
  }
}
