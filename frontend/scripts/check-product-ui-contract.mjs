import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const root = new URL("../src", import.meta.url).pathname;
const bannedUserCopy = [
  /SQLite/i,
  /Prisma/i,
  /Archive sync/i,
  /Persistence/i,
  /connected/i,
  /\b연결\b/,
  /대시보드/,
  /웜톤/,
  /"OPENROUTER"/,
  /"ANTHROPIC"/,
  /"HERMES"/,
  /"LOCAL"/,
  /"CUSTOM"/,
];
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
  if (/window\.confirm\s*\(|\bconfirm\s*\(/.test(content)) {
    violations.push(`${relative(root, path)} uses native browser confirm instead of in-app confirmation UI`);
  }
}

const dashboard = readFileSync(join(root, "components/dashboard/dashboard-client.tsx"), "utf8");
const library = readFileSync(join(root, "components/library/library-client.tsx"), "utf8");
const forms = readFileSync(join(root, "components/library/library-forms.tsx"), "utf8");
const detail = readFileSync(join(root, "components/skill/skill-detail-client.tsx"), "utf8");
const settings = readFileSync(join(root, "components/settings/settings-client.tsx"), "utf8");
const layout = readFileSync(join(root, "components/layout/sidebar.tsx"), "utf8");
const topHeader = readFileSync(join(root, "components/layout/top-header.tsx"), "utf8");
const appShell = readFileSync(join(root, "components/layout/app-shell.tsx"), "utf8");
const i18n = readFileSync(join(root, "lib/i18n.ts"), "utf8");
const api = readFileSync(join(root, "lib/api.ts"), "utf8");
const archiveAdapter = readFileSync(join(root, "lib/backend/archive.ts"), "utf8");
const store = readFileSync(join(root, "store/library-store.ts"), "utf8");
const agents = readFileSync(join(root, "app/agents/page.tsx"), "utf8");
const globals = readFileSync(join(root, "app/globals.css"), "utf8");

const requiredPageCopy = [
  ["dashboard guide", `${dashboard}\n${i18n}`, ["The Archive Guide", "The Archive Philosophy", "Getting Started", "Core Concepts", "On This Page", "Ask the Librarian"]],
  ["document shell", `${appShell}\n${layout}\n${topHeader}\n${globals}\n${i18n}`, ["archive-main", "Alexandria", "Archive", "Search skills, prompts, folders", "archive-right-rail", "#f6f3ec"]],
  ["library/i18n", `${library}\n${forms}\n${i18n}`, ["서재", "문서 유형", "신뢰 높은순", "총", "아카이브", "LibraryItemCreatePanel", "Preview / Lint"]],
  ["settings", `${settings}\n${i18n}`, ["언어", "한국어", "English", "서재 사용 환경"]],
  ["detail", `${detail}\n${i18n}`, ["Archive Controls", "사용 가이드 열기", "목차", "브라우저 팝업 없이"]],
];

const requiredFeatureContracts = [
  ["folder CRUD", `${api}\n${library}`, ["createCategory", "deleteCategory", "createCategoryMutation", "deleteCategoryMutation", "pendingCategoryDelete"]],
  ["direct item authoring", `${api}\n${library}\n${forms}`, ["createSkill", "createPrompt", "SkillCreateForm", "uploadSkillFile", "readAsText", "PromptFields"]],
  [
    "OpenAI and MINIO librarian providers",
    `${settings}\n${api}\n${store}\n${archiveAdapter}`,
    ["OPENAI", "MINIO", "minioPlacementHint"],
  ],
  [
    "settings information architecture",
    `${settings}\n${layout}`,
    [
      'href: "/settings"',
      'href: "/settings#librarians"',
      'activeSettingsSection === "library"',
      'activeSettingsSection === "librarians"',
    ],
  ],
  ["removed old agent panel", `${layout}\n${topHeader}\n${i18n}`, ["Library", "User Guide"]],
];

if (layout.includes('labelKey: "librarianSettings", href: "/settings"')) {
  violations.push("sidebar routes librarian settings to /settings instead of /settings#librarians");
}

for (const [name, content, required] of [...requiredPageCopy, ...requiredFeatureContracts]) {
  for (const label of required) {
    if (!content.includes(label)) {
      violations.push(`${name} page is missing required product contract: ${label}`);
    }
  }
}

for (const [name, content] of [
  ["sidebar", layout],
  ["top header", topHeader],
  ["agents", agents],
]) {
  for (const forbidden of ["currentAgent", "Claude 3.5", "현재 에이전트 메뉴", "const queue", "사서 정리 대기열", "서재 운영 신호"]) {
    if (content.includes(forbidden)) {
      violations.push(`${name} still exposes removed agent panel contract: ${forbidden}`);
    }
  }
}

if (violations.length > 0) {
  console.error(violations.join("\n"));
  process.exit(1);
}

console.log("product UI contract ok");
