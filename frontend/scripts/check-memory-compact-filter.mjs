import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const memoryCompacts = readFileSync(
  new URL("../src/components/memory/memory-compacts-client.tsx", import.meta.url),
  "utf8",
);
const filterUtils = readFileSync(new URL("../src/lib/filter-utils.ts", import.meta.url), "utf8");
const compactRouter = readFileSync(
  new URL(
    "../../backend/app/memory/interface/routers/memory_compact_router.py",
    import.meta.url,
  ),
  "utf8",
);
const compactRepository = readFileSync(
  new URL(
    "../../backend/app/memory/infrastructure/repositories/memory_compact_repository.py",
    import.meta.url,
  ),
  "utf8",
);

for (const required of [
  "FilterChipGroup",
  "variant=\"toolbar\"",
  "Displaying",
  "Filters \\(",
  "SlidersHorizontal",
  "compact-project",
  "compact-status",
  "compact-date-from",
  "compact-date-to",
  "Summary Period",
  "covered_after",
  "covered_before",
  "Clear Filters",
]) {
  assert.match(memoryCompacts, new RegExp(required), `Memory Compact filters are missing ${required}`);
}

assert.match(memoryCompacts, /type="date"/, "Memory Compact date controls must use browser date inputs.");
assert.match(memoryCompacts, /toUtcDateBoundaryIso/, "Memory Compact filters must use the shared UTC date boundary helper.");
assert.match(filterUtils, /setUTCHours\(23, 59, 59, 999\)/, "Memory Compact end dates must include the selected day through UTC day-end.");
assert.doesNotMatch(memoryCompacts, /<Select\b/, "Memory Compact filters must use direct selection chips instead of overlay selects.");

for (const required of [
  "covered_after: (?:datetime|AwareTimestamp) \\| None",
  "covered_before: (?:datetime|AwareTimestamp) \\| None",
]) {
  assert.match(compactRouter, new RegExp(required), `Memory Compact router is missing ${required}`);
}

for (const required of [
  "MemoryCompactORM.covered_to >= covered_after",
  "MemoryCompactORM.covered_from <= covered_before",
]) {
  assert.match(compactRepository, new RegExp(required.replaceAll(".", "\\.")), `Memory Compact repository is missing ${required}`);
}

console.log("memory compact filter contract ok");
