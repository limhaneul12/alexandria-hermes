import { NextResponse } from "next/server";

import { chatWithLibrarianInBackend } from "@/lib/backend/librarian-chat";
import { backendFailureResponse } from "../../_shared/backend-error-response";
import type { LibrarianChatRequestDTO } from "@/types/library";

export async function POST(request: Request) {
  try {
    const payload = (await request.json()) as LibrarianChatRequestDTO;
    return NextResponse.json(await chatWithLibrarianInBackend(payload));
  } catch (error) {
    return backendFailureResponse(error, "사서 대화를 처리하지 못했습니다.");
  }
}
