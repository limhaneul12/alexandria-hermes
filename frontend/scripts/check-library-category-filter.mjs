import assert from "node:assert/strict";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import ts from "typescript";

const helperPath = new URL("../src/lib/backend/archive-category-filter.ts", import.meta.url);
assert.equal(existsSync(helperPath), true, "archive category filter helper must exist");

const source = readFileSync(helperPath, "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.ESNext,
    target: ts.ScriptTarget.ES2022,
    strict: true,
  },
}).outputText;
const tempPath = join(tmpdir(), `archive-category-filter-${Date.now()}.mjs`);
writeFileSync(tempPath, compiled);
const mod = await import(pathToFileURL(tempPath));
assert.equal(typeof mod.collectCategoryTreeIds, "function", "collectCategoryTreeIds export is required");

const categories = [
  {
    id: "root",
    name: "Root",
    parent_id: null,
    position: 0,
    children: [
      {
        id: "child",
        name: "Child",
        parent_id: "root",
        position: 0,
        children: [
          {
            id: "grandchild",
            name: "Grandchild",
            parent_id: "child",
            position: 0,
            children: [],
          },
        ],
      },
    ],
  },
  {
    id: "other",
    name: "Other",
    parent_id: null,
    position: 1,
    children: [],
  },
];

assert.deepEqual(
  [...mod.collectCategoryTreeIds(categories, "root")].sort(),
  ["child", "grandchild", "root"],
  "selecting a folder must include the folder and all descendant folder ids",
);
assert.deepEqual(
  [...mod.collectCategoryTreeIds(categories, "child")].sort(),
  ["child", "grandchild"],
  "selecting a nested folder must include nested descendants",
);
assert.deepEqual(
  [...mod.collectCategoryTreeIds(categories, "missing")],
  [],
  "unknown category ids should produce an empty filter set",
);

console.log("library category descendant filter contract ok");
