import { NextResponse } from "next/server";

import { createCategoryInBackend } from "@/lib/backend/archive";
import { isRecord } from "../_shared/request-parsing";
import type { CategoryCreateDTO } from "@/types/library";

export async function POST(request: Request) {
  try {
    const rawBody = await request.json();
    if (!isRecord(rawBody)) {
      return NextResponse.json({ message: "폴더 정보를 다시 확인하세요." }, { status: 400 });
    }

    const name = typeof rawBody.name === "string" ? rawBody.name.trim() : "";
    const parentId = typeof rawBody.parentId === "string" && rawBody.parentId.trim()
      ? rawBody.parentId.trim()
      : null;

    if (!name) {
      return NextResponse.json({ message: "폴더 이름을 입력하세요." }, { status: 400 });
    }

    const payload: CategoryCreateDTO = { name, parentId };
    const category = await createCategoryInBackend(payload);
    return NextResponse.json(category, { status: 201 });
  } catch {
    return NextResponse.json(
      { message: "폴더를 만들지 못했습니다. 입력값을 확인하세요." },
      { status: 502 },
    );
  }
}
