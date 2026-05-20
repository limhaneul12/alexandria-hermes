import { NextResponse } from "next/server";

import {
  createLibrarianProviderInBackend,
  loadLibrarianProvidersFromBackend,
} from "@/lib/backend/librarians";
import { backendFailureResponse } from "../_shared/backend-error-response";
import { routeErrorPayload } from "@/lib/backend/route-errors";
import {
  isCredentialMode,
  isProviderType,
  isRecord,
  safeLibrarianProviderConfig,
} from "../_shared/request-parsing";
import type { LibrarianProviderCreateDTO } from "@/types/library";

export async function GET() {
  try {
    return NextResponse.json(await loadLibrarianProvidersFromBackend());
  } catch (error) {
    return backendFailureResponse(error, "Librarian provider list failed", "LIBRARIAN_PROVIDER_LIST_FAILED");
  }
}

export async function POST(request: Request) {
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
  const name = typeof body.name === "string" ? body.name.trim() : "";
  const credential = typeof body.credential === "string" ? body.credential.trim() : "";

  if (!name || !isProviderType(body.providerType) || !isCredentialMode(body.authType)) {
    return NextResponse.json(
      routeErrorPayload("INVALID_LIBRARIAN_PROVIDER_PAYLOAD", "Invalid librarian provider payload."),
      { status: 400 },
    );
  }
  if (body.authType === "API_KEY" && !credential) {
    return NextResponse.json(
      routeErrorPayload("INVALID_LIBRARIAN_PROVIDER_PAYLOAD", "Invalid librarian provider payload."),
      { status: 400 },
    );
  }

  const payload: LibrarianProviderCreateDTO = {
    name,
    providerType: body.providerType,
    authType: body.authType,
    enabled: typeof body.enabled === "boolean" ? body.enabled : true,
    config: safeLibrarianProviderConfig(body.config, body.providerType),
  };
  if (body.authType === "API_KEY") {
    payload.credential = credential;
  }
  try {
    const provider = await createLibrarianProviderInBackend(payload);
    return NextResponse.json(provider, { status: 201 });
  } catch (error) {
    return backendFailureResponse(
      error,
      "Librarian provider save failed",
      "LIBRARIAN_PROVIDER_SAVE_FAILED",
    );
  }
}
