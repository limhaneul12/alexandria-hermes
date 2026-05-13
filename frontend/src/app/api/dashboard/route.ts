import { NextResponse } from "next/server";

import { loadDashboardFromBackend } from "@/lib/backend/archive";

export async function GET() {
  return NextResponse.json(await loadDashboardFromBackend());
}
