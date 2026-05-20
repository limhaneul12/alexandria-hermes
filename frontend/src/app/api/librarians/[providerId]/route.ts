import { NextResponse } from "next/server";

import {
  deleteLibrarianProviderInBackend,
  updateLibrarianProviderInBackend,
} from "@/lib/backend/librarians";
import { backendFailureResponse } from "../../_shared/backend-error-response";
import { routeErrorPayload } from "@/lib/backend/route-errors";
import {
  isCredentialMode,
  isProviderType,
  isRecord,
  safeLibrarianProviderConfig,
} from "../../_shared/request-parsing";
import type { LibrarianProviderUpdateDTO } from "@/types/library";

export async function PATCH(
  request: Request,
  context: { params: Promise<{ providerId: string }> },
) {
  const { providerId } = await context.params;
  let rawBody: unknown;
  try {
    rawBody = await request.json();
  } catch {
    return NextResponse.json(routeErrorPayload("INVALID_LIBRARIAN_PROVIDER_PAYLOAD", "Invalid librarian provider payload."), { status: 400 });
  }
  if (!isRecord(rawBody)) {
    return NextResponse.json(routeErrorPayload("INVALID_LIBRARIAN_PROVIDER_PAYLOAD", "Invalid librarian provider payload."), { status: 400 });
  }
  const body = rawBody;
  const payload: LibrarianProviderUpdateDTO = {};

  if (typeof body.name === "string" && body.name.trim()) payload.name = body.name.trim();
  if (isProviderType(body.providerType)) payload.providerType = body.providerType;
  if (isCredentialMode(body.authType)) payload.authType = body.authType;
  if (typeof body.enabled === "boolean") payload.enabled = body.enabled;
  if ("config" in body) {
    const configProviderType = isProviderType(body.providerType)
      ? body.providerType
      : isRecord(body.config) && ("device_authorization_url" in body.config || "device_token_url" in body.config || "token_url" in body.config || "issuer" in body.config)
        ? "OPENAI_CODEX"
        : "OPENAI";
    payload.config = safeLibrarianProviderConfig(body.config, configProviderType);
  }
  if (payload.authType === "API_KEY" && typeof body.credential === "string" && body.credential.trim()) {
    payload.credential = body.credential.trim();
  }

  if (Object.keys(payload).length === 0) {
    return NextResponse.json(
      routeErrorPayload("EMPTY_LIBRARIAN_PROVIDER_UPDATE", "No librarian provider changes were supplied."),
      { status: 400 },
    );
  }

  try {
    return NextResponse.json(await updateLibrarianProviderInBackend(providerId, payload));
  } catch (error) {
    return backendFailureResponse(error, "Librarian provider update failed", "LIBRARIAN_PROVIDER_UPDATE_FAILED");
  }
}

export async function DELETE(
  _request: Request,
  context: { params: Promise<{ providerId: string }> },
) {
  const { providerId } = await context.params;
  try {
    await deleteLibrarianProviderInBackend(providerId);
    return new NextResponse(null, { status: 204 });
  } catch (error) {
    return backendFailureResponse(error, "Librarian provider delete failed", "LIBRARIAN_PROVIDER_DELETE_FAILED");
  }
}
