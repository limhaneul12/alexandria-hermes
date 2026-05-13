import { NextResponse } from "next/server";

import {
  createLibrarianProviderInBackend,
  loadLibrarianProvidersFromBackend,
} from "@/lib/backend/librarians";
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

export async function GET() {
  try {
    return NextResponse.json(await loadLibrarianProvidersFromBackend());
  } catch {
    return NextResponse.json(
      { message: "사서 인증 목록을 불러오지 못했습니다." },
      { status: 502 },
    );
  }
}

export async function POST(request: Request) {
  try {
    const rawBody = await request.json();
    if (!isRecord(rawBody)) {
      return NextResponse.json({ message: "사서 인증 정보를 다시 확인하세요." }, { status: 400 });
    }
    const body = rawBody;
    const name = typeof body.name === "string" ? body.name.trim() : "";
    const credential = typeof body.credential === "string" ? body.credential.trim() : "";

    if (!name || !credential || !isProviderType(body.providerType) || !isCredentialMode(body.authType)) {
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
      config: safeConfig(body.config),
      credential,
    };
    const provider = await createLibrarianProviderInBackend(payload);
    return NextResponse.json(provider, { status: 201 });
  } catch {
    return NextResponse.json(
      { message: "사서 인증을 저장하지 못했습니다. 설정을 확인하세요." },
      { status: 502 },
    );
  }
}
