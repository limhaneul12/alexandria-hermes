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
  /FilterChip/,
  "Ask Librarian quick prompts must use the shared filter chip UI.",
);
assert.match(
  source,
  /setResponse\(null\);[\s\S]*const result = await askLibrarian/,
  "submitting a new prompt should clear stale responses before awaiting the librarian",
);
assert.match(
  source,
  /kicker:\s*"도움이 필요하신가요\?"/,
  "Korean Ask Librarian copy must not leave the kicker in English",
);
const koreanBlock = source.match(/if \(language === "ko"\) \{[\s\S]*?\n  \}\n  return \{/u)?.[0] ?? "";
assert.notEqual(koreanBlock, "", "Korean Ask Librarian copy block must be present");
assert.doesNotMatch(
  koreanBlock,
  /prompt:\s*"(?:Find|Recommend|Recall|Draft) /,
  "Korean quick prompt examples must be localized before inserting into the textarea",
);
assert.match(
  source,
  /closePanel:\s*"닫기"/,
  "the close-panel aria label must be localized through the widget copy",
);
assert.match(
  source,
  /job:\s*"작업"/,
  "the Job label must have Korean copy instead of hardcoded English UI text",
);

console.log("ask librarian widget delegation contract ok");
