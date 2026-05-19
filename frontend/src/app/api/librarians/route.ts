import { NextResponse } from "next/server";

import {
  createLibrarianProviderInBackend,
  loadLibrarianProvidersFromBackend,
} from "@/lib/backend/librarians";
import { backendFailureResponse } from "../_shared/backend-error-response";
import {
  LIBRARIAN_AUTH_TYPES,
  PROVIDER_TYPES,
  type LibrarianProviderCreateDTO,
  type LibrarianProviderCredentialMode,
  type ProviderType,
} from "@/types/library";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function safeConfig(value: unknown, providerType: ProviderType): Record<string, unknown> {
  if (!isRecord(value)) return {};
  const config: Record<string, unknown> = {};
  if (providerType === "OPENAI_CODEX") {
    for (const key of ["device_authorization_url", "device_token_url", "issuer", "redirect_uri", "token_url", "verification_uri", "client_id", "scope"] as const) {
      const rawValue = value[key];
      if (typeof rawValue === "string" && rawValue.trim()) {
        config[key] = rawValue.trim();
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

export async function GET() {
  try {
    return NextResponse.json(await loadLibrarianProvidersFromBackend());
  } catch (error) {
    return backendFailureResponse(error, "사서 인증 목록을 불러오지 못했습니다.");
  }
}

export async function POST(request: Request) {
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
  const name = typeof body.name === "string" ? body.name.trim() : "";
  const credential = typeof body.credential === "string" ? body.credential.trim() : "";

  if (!name || !isProviderType(body.providerType) || !isCredentialMode(body.authType)) {
    return NextResponse.json(
      { message: "사서 인증 정보를 다시 확인하세요." },
      { status: 400 },
    );
  }
  if (body.authType === "API_KEY" && !credential) {
    return NextResponse.json(
      { message: "사서 인증 정보를 다시 확인하세요." },
      { status: 400 },
    );
  }

  const payload: LibrarianProviderCreateDTO = {
    name,
    providerType: body.providerType,
    authType: body.authType,
    enabled: typeof body.enabled === "boolean" ? body.enabled : true,
    config: safeConfig(body.config, body.providerType),
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
      "사서 인증을 저장하지 못했습니다. 설정을 확인하세요.",
    );
  }
}
