import { NextResponse } from "next/server";

import {
  deleteLibrarianProviderInBackend,
  updateLibrarianProviderInBackend,
} from "@/lib/backend/librarians";
import { backendFailureResponse } from "../../_shared/backend-error-response";
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

function safeConfig(value: unknown, providerType: ProviderType): Record<string, unknown> {
  if (!isRecord(value)) return {};
  const config: Record<string, unknown> = {};
  if (providerType === "MINIO") {
    if (typeof value.endpoint === "string" && value.endpoint.trim()) {
      config.endpoint = value.endpoint.trim();
    }
    if (typeof value.bucket === "string" && value.bucket.trim()) {
      config.bucket = value.bucket.trim();
    }
    if (typeof value.prefix === "string") config.prefix = value.prefix.trim();
    if (typeof value.region === "string" && value.region.trim()) {
      config.region = value.region.trim();
    }
    if (typeof value.use_ssl === "boolean") config.use_ssl = value.use_ssl;
  } else if (providerType === "OPENAI_CODEX") {
    for (const key of ["device_authorization_url", "device_token_url", "issuer", "redirect_uri", "token_url", "verification_uri", "client_id", "scope"] as const) {
      if (typeof value[key] === "string" && value[key].trim()) {
        config[key] = value[key].trim();
      }
    }
  } else {
    if (typeof value.model === "string" && value.model.trim()) config.model = value.model.trim();
    if (typeof value.base_url === "string" && value.base_url.trim()) {
      config.base_url = value.base_url.trim();
    }
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
  let rawBody: unknown;
  try {
    rawBody = await request.json();
  } catch {
    return NextResponse.json({ message: "사서 인증 정보를 다시 확인하세요." }, { status: 400 });
  }
  if (!isRecord(rawBody)) {
    return NextResponse.json({ message: "사서 인증 정보를 다시 확인하세요." }, { status: 400 });
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
      : isRecord(body.config) && ("endpoint" in body.config || "bucket" in body.config)
        ? "MINIO"
        : isRecord(body.config) && ("device_authorization_url" in body.config || "device_token_url" in body.config || "token_url" in body.config || "issuer" in body.config)
          ? "OPENAI_CODEX"
          : "OPENAI";
    payload.config = safeConfig(body.config, configProviderType);
  }
  if (payload.authType === "API_KEY" && typeof body.credential === "string" && body.credential.trim()) {
    payload.credential = body.credential.trim();
  }

  if (Object.keys(payload).length === 0) {
    return NextResponse.json(
      { message: "변경할 사서 인증 정보가 없습니다." },
      { status: 400 },
    );
  }

  try {
    return NextResponse.json(await updateLibrarianProviderInBackend(providerId, payload));
  } catch (error) {
    return backendFailureResponse(error, "사서 인증을 업데이트하지 못했습니다.");
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
    return backendFailureResponse(error, "사서 인증을 삭제하지 못했습니다.");
  }
}
