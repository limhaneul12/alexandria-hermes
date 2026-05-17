import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";

const sidebar = readFileSync(new URL("../src/components/layout/sidebar.tsx", import.meta.url), "utf8");
const libraryClient = readFileSync(new URL("../src/components/library/library-client.tsx", import.meta.url), "utf8");
const forms = readFileSync(new URL("../src/components/library/library-forms.tsx", import.meta.url), "utf8");
const contextVault = readFileSync(new URL("../src/components/context/context-vault-client.tsx", import.meta.url), "utf8");
const librarianChat = readFileSync(new URL("../src/components/librarian/librarian-chat-client.tsx", import.meta.url), "utf8");
const librarianChatBackend = readFileSync(new URL("../src/lib/backend/librarian-chat.ts", import.meta.url), "utf8");

for (const route of ["/library/skills", "/library/prompts", "/library/skills/new", "/library/prompts/new", "/librarian/chat"]) {
  assert.match(sidebar, new RegExp(route.replaceAll("/", "\\/")), `sidebar must expose ${route}`);
}
assert.match(sidebar, /librarianChat/, "sidebar must expose 사서와 얘기하기 via i18n key");
for (const removed of ["favorites", "recommendations", "categories", "recent"]) {
  assert.doesNotMatch(sidebar, new RegExp(`labelKey:\\s*["']${removed}["']`), `${removed} must not remain as a top-level library nav entry`);
}
assert.doesNotMatch(sidebar, /\/library\?create=/, "sidebar must not use query-owned create routes");
assert.match(libraryClient, /router\.replace\("\/library\/skills\/new"/, "legacy ?create=skill must redirect to dedicated route");
assert.match(libraryClient, /router\.replace\("\/library\/prompts\/new"/, "legacy ?create=prompt must redirect to dedicated route");

for (const file of [
  "../src/app/library/skills/page.tsx",
  "../src/app/library/prompts/page.tsx",
  "../src/app/library/skills/new/page.tsx",
  "../src/app/library/prompts/new/page.tsx",
  "../src/app/librarian/chat/page.tsx",
]) {
  assert.equal(existsSync(new URL(file, import.meta.url)), true, `${file} must exist`);
}
for (const [label, source] of [["library client", libraryClient], ["library forms", forms], ["context vault", contextVault]]) {
  assert.doesNotMatch(source, /<select\b/, `${label} must use Alexandria Select instead of native select`);
}
assert.doesNotMatch(librarianChat, /@\/components\/ui\/select/, "librarian chat must not expand Alexandria Select beyond the approved scope");
assert.doesNotMatch(librarianChatBackend, /\/library\/items\//, "librarian chat source refs must use existing library detail routes");
assert.match(
  librarianChatBackend,
  /detailPath:\s*`\/library\/\$\{categorySlug\}\/\$\{encodeURIComponent\(hit\.id\)\}`/,
  "librarian chat source refs must include category detail paths",
);

console.log("library UI navigation contract ok");
