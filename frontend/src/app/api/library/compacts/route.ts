import { NextResponse } from "next/server";

import { parseMemoryCompactCreateBody } from "./compact-route-payload";
import {
  createMemoryCompactInBackend,
  loadMemoryCompactsFromBackend,
} from "@/lib/backend/memory-compacts";
import { backendErrorResponse, routeErrorPayload } from "@/lib/backend/route-errors";

export async function GET(request: Request) {
  try {
    return NextResponse.json(
      await loadMemoryCompactsFromBackend(new URL(request.url).searchParams),
    );
  } catch (error) {
    return backendErrorResponse(error, "Memory Compact list failed");
  }
}

export async function POST(request: Request) {
  let rawBody: unknown;
  try {
    rawBody = await request.json();
  } catch {
    return NextResponse.json(
      routeErrorPayload("INVALID_MEMORY_COMPACT_PAYLOAD", "Invalid Memory Compact payload."),
      { status: 400 },
    );
  }
  const parsed = parseMemoryCompactCreateBody(rawBody);
  if (!parsed.ok) {
    return NextResponse.json(routeErrorPayload(parsed.code, parsed.message), {
      status: 400,
    });
  }
  try {
    return NextResponse.json(await createMemoryCompactInBackend(parsed.payload), {
      status: 201,
    });
  } catch (error) {
    return backendErrorResponse(error, "Memory Compact create failed");
  }
}
