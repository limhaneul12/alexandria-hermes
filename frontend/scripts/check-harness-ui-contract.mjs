import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";

const sidebar = readFileSync(new URL("../src/components/layout/sidebar.tsx", import.meta.url), "utf8");
const harnessClient = readFileSync(new URL("../src/components/harness/harness-guidebook-client.tsx", import.meta.url), "utf8");
const harnessDetail = readFileSync(new URL("../src/components/harness/harness-detail-client.tsx", import.meta.url), "utf8");
const api = readFileSync(new URL("../src/lib/api.ts", import.meta.url), "utf8");
const backendHarnesses = readFileSync(new URL("../src/lib/backend/harnesses.ts", import.meta.url), "utf8");
const types = readFileSync(new URL("../src/types/library.ts", import.meta.url), "utf8");
const i18n = readFileSync(new URL("../src/lib/i18n.ts", import.meta.url), "utf8");
const backendRouter = readFileSync(new URL("../../backend/app/memory/interface/routers/context_router.py", import.meta.url), "utf8");
const mcpGateway = readFileSync(new URL("../../backend/app/mcp_server/backend_tool_gateway.py", import.meta.url), "utf8");

for (const file of [
  "../src/app/harnesses/page.tsx",
  "../src/app/harnesses/[contextId]/page.tsx",
  "../src/app/api/library/harnesses/route.ts",
  "../src/app/api/library/harnesses/check/route.ts",
  "../src/app/api/library/harnesses/[contextId]/route.ts",
  "../src/app/api/library/harnesses/[contextId]/archive/route.ts",
]) {
  assert.equal(existsSync(new URL(file, import.meta.url)), true, `${file} must exist`);
}

assert.match(sidebar, /href:\s*"\/harnesses"/, "sidebar must expose the Harness Guidebook route");
assert.match(sidebar, /harnessGuidebook/, "sidebar must use the harness i18n key");
for (const required of [
  "Harness Guidebook",
  "Reusable Field Manuals",
  "book-cover",
  "Draft Harness Page",
  "Check Result",
  "fetchHarnesses",
  "captureHarness",
  "checkHarness",
  "archiveHarness",
]) {
  assert.match(`${harnessClient}\n${i18n}`, new RegExp(required), `Harness list UI missing ${required}`);
}
for (const required of [
  "Harness Field Manual",
  "Reusable Procedure",
  "Safety Notes",
  "Trigger / Environment",
  "recordContextAccessEvent",
]) {
  assert.match(`${harnessDetail}\n${i18n}`, new RegExp(required), `Harness detail UI missing ${required}`);
}
assert.match(harnessClient, /useLibraryStore/, "Harness list UI must use language state");
assert.match(harnessDetail, /useLibraryStore/, "Harness detail UI must use language state");
assert.match(i18n, /longTermMemory/, "sidebar memory section must be localized");
for (const required of [
  "fetchHarnesses",
  "fetchHarness",
  "captureHarness",
  "checkHarness",
  "archiveHarness",
]) {
  assert.match(api, new RegExp(`export function ${required}`), `API helper missing ${required}`);
}
for (const route of [
  "/memory/contexts/harnesses",
  "/memory/contexts/harnesses/capture",
  "/memory/contexts/harnesses/check",
]) {
  assert.match(backendHarnesses, new RegExp(route.replaceAll("/", "\\/")), `frontend backend adapter must call ${route}`);
}
assert.match(types, /type HarnessExecutionMetadataDTO/, "types must define harness metadata DTO");
assert.match(types, /type HarnessCaptureDTO/, "types must define harness capture DTO");
assert.match(backendRouter, /"\/harnesses\/check"/, "backend router must expose harness check");
assert.match(backendRouter, /"\/harnesses"/, "backend router must expose harness list");
assert.match(mcpGateway, /alexandria_list_harnesses/, "MCP gateway must expose harness list wrapper");
assert.doesNotMatch(backendHarnesses, /\/library\/harness/, "Harness UI must not call Library CRUD harness routes");

console.log("harness UI contract ok");
