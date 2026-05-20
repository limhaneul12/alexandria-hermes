import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const contextVault = readFileSync(new URL("../src/components/context/context-vault-client.tsx", import.meta.url), "utf8");
const filterChipGroup = readFileSync(new URL("../src/components/ui/filter-chip-group.tsx", import.meta.url), "utf8");
const filterUtils = readFileSync(new URL("../src/lib/filter-utils.ts", import.meta.url), "utf8");
const backendContexts = readFileSync(new URL("../src/lib/backend/contexts.ts", import.meta.url), "utf8");
const contextRoute = readFileSync(new URL("../src/app/api/library/contexts/route.ts", import.meta.url), "utf8");

for (const required of [
  "FilterChipGroup",
  "variant=\"toolbar\"",
  "Displaying",
  "Filters \\(",
  "SlidersHorizontal",
  "dateField",
  "Created Date",
  "Updated Date",
  "context-project",
  "context-tag",
  "date-from",
  "date-to",
  "created_after",
  "created_before",
  "updated_after",
  "updated_before",
]) {
  assert.match(contextVault, new RegExp(required), `Context Vault date filter is missing ${required}`);
}

assert.match(contextVault, /type="date"/, "Context Vault date range controls must use browser date inputs.");
assert.match(contextVault, /toUtcDateBoundaryIso/, "Context Vault must use the shared UTC date boundary helper.");
assert.match(filterUtils, /setUTCHours\(23, 59, 59, 999\)/, "Date filter end dates must include the selected day through UTC day-end.");
assert.doesNotMatch(contextVault, /<Select\b/, "Context Vault filters must use in-flow direct selection chips instead of overlay selects.");
assert.match(filterChipGroup, /overflow-y-auto/, "Direct filter choices must scroll inside their filter box rather than overlapping cards.");
assert.doesNotMatch(filterChipGroup, /\babsolute\b|\bz-50\b/, "Direct filter choices must stay in document flow and avoid overlay stacking.");
assert.match(backendContexts, /\/memory\/contexts\$\{query \? `\?\$\{query\}` : ""\}/, "Frontend backend adapter must forward date query params without dropping them.");
assert.doesNotMatch(contextRoute, /export async function POST/, "Context list route must stay read-only while adding date filters.");

console.log("context vault date filter contract ok");
