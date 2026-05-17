import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const chatBackend = readFileSync(new URL("../src/lib/backend/librarian-chat.ts", import.meta.url), "utf8");
const chatRoute = readFileSync(new URL("../src/app/api/librarians/chat/route.ts", import.meta.url), "utf8");

assert.match(
  chatRoute,
  /chatWithLibrarianInBackend/,
  "/api/librarians/chat must use the server-side chat orchestrator",
);
assert.match(
  chatBackend,
  /response\.status === "COMPLETED"[\s\S]*delegate\.status === "COMPLETED"/,
  "chat orchestration must require a completed top-level ask and completed delegate",
);
assert.match(
  chatBackend,
  /delegatedJobId:\s*null/,
  "chat orchestration must not expose a delegated job id when delegation did not complete",
);
assert.match(
  chatBackend,
  /delegateFailureAnswer/,
  "chat orchestration must surface skipped delegate evidence to the UI",
);

console.log("librarian chat delegation contract ok");
