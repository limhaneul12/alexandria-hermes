import { NextResponse } from "next/server";

import { deleteLibraryItemInBackend, loadLibraryItemDetailFromBackend } from "@/lib/backend/archive";
import { BackendRequestError } from "@/lib/backend/client";

export async function GET(
  _request: Request,
  context: { params: Promise<{ itemId: string }> },
) {
  const { itemId } = await context.params;
  const item = await loadLibraryItemDetailFromBackend(itemId);

  if (!item) {
    return NextResponse.json({ message: "Library item not found" }, { status: 404 });
  }

  return NextResponse.json(item);
}

export async function DELETE(
  _request: Request,
  context: { params: Promise<{ itemId: string }> },
) {
  const { itemId } = await context.params;
  try {
    const item = await loadLibraryItemDetailFromBackend(itemId);
    if (!item) return NextResponse.json({ message: "Library item not found" }, { status: 404 });
    await deleteLibraryItemInBackend(item);
    return new NextResponse(null, { status: 204 });
  } catch (error) {
    return NextResponse.json(
      { message: "Library item delete failed" },
      { status: error instanceof BackendRequestError ? error.status : 502 },
    );
  }
}
