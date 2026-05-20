import { NextResponse } from "next/server";

import { chatWithLibrarianInBackend } from "@/lib/backend/librarian-chat";
import { routeErrorPayload } from "@/lib/backend/route-errors";
import { backendFailureResponse } from "../../_shared/backend-error-response";
import { parseLibrarianChatBody } from "./chat-route-payload";

export async function POST(request: Request) {
  let rawBody: unknown;
  try {
    rawBody = await request.json();
  } catch {
    return NextResponse.json(
      routeErrorPayload("INVALID_LIBRARIAN_CHAT_PAYLOAD", "Invalid librarian chat payload."),
      { status: 400 },
    );
  }
  const parsed = parseLibrarianChatBody(rawBody);
  if (!parsed.ok) {
    return NextResponse.json(routeErrorPayload(parsed.code, parsed.message), {
      status: 400,
    });
  }
  try {
    return NextResponse.json(await chatWithLibrarianInBackend(parsed.payload));
  } catch (error) {
    return backendFailureResponse(
      error,
      "Librarian chat failed.",
      "LIBRARIAN_CHAT_FAILED",
    );
  }
}
