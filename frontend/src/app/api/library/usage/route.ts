import { NextResponse } from "next/server";

import { recordLibraryUsageInBackend } from "@/lib/backend/archive";
import { backendErrorResponse } from "@/lib/backend/route-errors";
import type { LibraryUsageRecordCreateDTO } from "@/types/library";

export async function POST(request: Request) {
  try {
    const payload = (await request.json()) as LibraryUsageRecordCreateDTO;
    return NextResponse.json(await recordLibraryUsageInBackend(payload), { status: 201 });
  } catch (error) {
    return backendErrorResponse(error, "Library usage record failed");
  }
}
