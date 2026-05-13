import { NextResponse } from "next/server";

import { updateLibrarianProviderInBackend } from "@/lib/backend/librarians";
import {
  LIBRARIAN_AUTH_TYPES,
  PROVIDER_TYPES,
  type LibrarianProviderCredentialMode,
  type LibrarianProviderUpdateDTO,
  type ProviderType,
} from "@/types/library";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function safeConfig(value: unknown): Record<string, unknown> {
  if (!isRecord(value)) return {};
  const config: Record<string, unknown> = {};
  if (typeof value.model === "string" && value.model.trim()) config.model = value.model.trim();
  if (typeof value.base_url === "string" && value.base_url.trim()) {
    config.base_url = value.base_url.trim();
  }
  return config;
}

function isProviderType(value: unknown): value is ProviderType {
  return typeof value === "string" && (PROVIDER_TYPES as readonly string[]).includes(value);
}

function isCredentialMode(value: unknown): value is LibrarianProviderCredentialMode {
  return typeof value === "string" && (LIBRARIAN_AUTH_TYPES as readonly string[]).includes(value);
}

export async function PATCH(
  request: Request,
  context: { params: Promise<{ providerId: string }> },
) {
  const { providerId } = await context.params;
  try {
    const rawBody = await request.json();
    if (!isRecord(rawBody)) {
      return NextResponse.json({ message: "사서 인증 정보를 다시 확인하세요." }, { status: 400 });
    }
    const body = rawBody;
    const payload: LibrarianProviderUpdateDTO = {};

    if (typeof body.name === "string" && body.name.trim()) payload.name = body.name.trim();
    if (isProviderType(body.providerType)) payload.providerType = body.providerType;
    if (isCredentialMode(body.authType)) payload.authType = body.authType;
    if (typeof body.enabled === "boolean") payload.enabled = body.enabled;
    if ("config" in body) payload.config = safeConfig(body.config);
    if (typeof body.credential === "string" && body.credential.trim()) {
      payload.credential = body.credential.trim();
    }

    if (Object.keys(payload).length === 0) {
      return NextResponse.json(
        { message: "변경할 사서 인증 정보가 없습니다." },
        { status: 400 },
      );
    }

    return NextResponse.json(await updateLibrarianProviderInBackend(providerId, payload));
  } catch {
    return NextResponse.json(
      { message: "사서 인증을 업데이트하지 못했습니다." },
      { status: 502 },
    );
  }
}
