import assert from "node:assert/strict";

import { existsSync, readFileSync } from "node:fs";

const archivePath = new URL("../src/lib/backend/archive.ts", import.meta.url);
const libraryClientPath = new URL("../src/components/library/library-client.tsx", import.meta.url);
assert.equal(existsSync(archivePath), true, "archive backend adapter must exist");
assert.equal(existsSync(libraryClientPath), true, "library client must exist");

const archiveSource = readFileSync(archivePath, "utf8");
const libraryClientSource = readFileSync(libraryClientPath, "utf8");

assert.match(
  archiveSource,
  /params\.append\("item_types", "SKILL"\)/,
  "library backend adapter must default candidate search to visible skill rows",
);
assert.match(
  archiveSource,
  /params\.append\("item_types", "PROMPT"\)/,
  "library backend adapter must default candidate search to visible prompt rows",
);
assert.match(
  archiveSource,
  /params\.set\("category_id", selectedCategory\.id\)/,
  "category filtering must be sent to backend before candidate pagination",
);
assert.match(
  archiveSource,
  /params\.set\("include_descendant_categories", "true"\)/,
  "category filtering must include descendant categories before pagination",
);
assert.match(
  archiveSource,
  /function isVisibleSearchHit/,
  "candidate card mapping must guard against non-visible backend item types",
);
for (const required of [
  "FilterChipGroup",
  "SlidersHorizontal",
  "library-updated-from",
  "library-updated-to",
  "updated_after",
  "updated_before",
]) {
  assert.match(libraryClientSource, new RegExp(required), `library filters are missing ${required}`);
}
assert.match(libraryClientSource, /type="date"/, "library filters must include browser date inputs.");
assert.doesNotMatch(
  libraryClientSource,
  /@\/components\/ui\/select/,
  "library list filters must avoid overlay Select controls that cover results.",
);
assert.match(
  archiveSource,
  /params\.set\("updated_after", updatedAfter\)/,
  "library backend adapter must forward updated-after filters before pagination",
);
assert.match(
  archiveSource,
  /params\.set\("updated_before", updatedBefore\)/,
  "library backend adapter must forward updated-before filters before pagination",
);

console.log("library category descendant filter contract ok");
