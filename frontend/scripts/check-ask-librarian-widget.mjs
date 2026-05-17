import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source = readFileSync(new URL("../src/components/librarian/ask-librarian-widget.tsx", import.meta.url), "utf8");

assert.match(
  source,
  /delegateToLibrarian:\s*true/,
  "the interactive Ask Librarian UI must execute an available librarian provider, not only return a route preview",
);
assert.match(
  source,
  /setResponse\(null\);[\s\S]*const result = await askLibrarian/,
  "submitting a new prompt should clear stale responses before awaiting the librarian",
);

console.log("ask librarian widget delegation contract ok");
