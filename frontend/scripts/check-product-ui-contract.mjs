import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const root = new URL("../src", import.meta.url).pathname;
const bannedUserCopy = [/SQLite/i, /Prisma/i, /Archive sync/i, /Persistence/i, /connected/i, /연결/];
const checkedExtensions = new Set([".ts", ".tsx"]);

function walk(dir) {
  return readdirSync(dir).flatMap((entry) => {
    const path = join(dir, entry);
    const stat = statSync(path);
    if (stat.isDirectory()) return walk(path);
    if (![...checkedExtensions].some((extension) => path.endsWith(extension))) return [];
    return [path];
  });
}

const violations = [];
for (const path of walk(root)) {
  const content = readFileSync(path, "utf8");
  for (const pattern of bannedUserCopy) {
    if (pattern.test(content)) {
      violations.push(`${relative(root, path)} contains banned product copy: ${pattern}`);
    }
  }
}

const dashboard = readFileSync(join(root, "components/dashboard/dashboard-client.tsx"), "utf8");
const library = readFileSync(join(root, "components/library/library-client.tsx"), "utf8");
const detail = readFileSync(join(root, "components/skill/skill-detail-client.tsx"), "utf8");

const requiredPageCopy = [
  ["dashboard", dashboard, ["Grand Archive", "최근에 가져간 스킬", "추천 아카이브"]],
  ["library", library, ["서재", "아이템 검색", "신뢰 높은순"]],
  ["detail", detail, ["스킬 상세 열람", "사용 가이드 열기", "목차"]],
];

for (const [name, content, required] of requiredPageCopy) {
  for (const label of required) {
    if (!content.includes(label)) {
      violations.push(`${name} page is missing required product copy: ${label}`);
    }
  }
}

if (violations.length > 0) {
  console.error(violations.join("\n"));
  process.exit(1);
}

console.log("product UI contract ok");
