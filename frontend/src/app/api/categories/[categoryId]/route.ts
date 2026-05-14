import { NextResponse } from "next/server";

import { deleteCategoryInBackend } from "@/lib/backend/archive";
import { BackendRequestError } from "@/lib/backend/client";

export async function DELETE(
  _request: Request,
  context: { params: Promise<{ categoryId: string }> },
) {
  const { categoryId } = await context.params;
  try {
    await deleteCategoryInBackend(categoryId);
    return new Response(null, { status: 204 });
  } catch (error) {
    return NextResponse.json(
      { message: "폴더를 삭제하지 못했습니다." },
      { status: error instanceof BackendRequestError ? error.status : 502 },
    );
  }
}
