import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const checks = [
  {
    file: "src/components/dashboard/dashboard-client.tsx",
    banned: [
      "Our goal is simple:",
      "Collect the best. Connect intelligently.",
      "Examples",
      "The Archive Philosophy",
      "Key Features",
      "Get help from your AI librarian.",
      "Latest Reading",
      "How to Create a Skill",
    ],
  },
  {
    file: "src/components/skill/skill-detail-client.tsx",
    banned: [
      "Archive Controls",
      "Removal panel",
      "삭제 확인은 브라우저 팝업 없이 이 카드 안에서 처리합니다.",
      "Prompt Body",
      "Fill Variables",
      "Copy Prompt",
      "Self-acquisition evidence",
      "Evidence URLs",
      "등록된 변수가 없습니다.",
      "아직 근거 URL이 없습니다.",
      "Prompt Reading Room",
      "Prompt Domain",
      "\"Variables\"",
      "Computer Science",
    ],
  },
  {
    file: "src/components/content/content-viewer.tsx",
    banned: ["원본보기 Raw", "보기"],
  },
  {
    file: "src/components/content/markdown-content.tsx",
    banned: ["표시할 본문이 없습니다."],
  },
  {
    file: "src/components/activity/recent-activity-list.tsx",
    banned: ["아직 기록된 조회/사용 이력이 없습니다."],
  },
  {
    file: "src/components/library/library-client.tsx",
    banned: [
      "내 서재",
      "폴더 단위로 스킬과 프롬프트를 탐색하고",
      "All Types",
      "All Categories",
      "All Tags",
      "Popular",
      "Shelf Browser",
      "What are you looking for?",
      ">Folder",
      "폴더를 삭제할까요?",
      "총 ",
      "아카이브 후보를 표시합니다.",
      "새 스킬/프롬프트를 만들거나",
    ],
  },
  {
    file: "src/components/library/library-item-list-client.tsx",
    banned: [
      "내 스킬",
      "내 프롬프트",
      "폴더 경로와 무관하게 모든 스킬",
      "flat list",
    ],
  },
  {
    file: "src/components/library/library-breadcrumb.tsx",
    banned: ["내 서재"],
  },
  {
    file: "src/components/library/library-folder-browser.tsx",
    banned: ["하위 폴더", "선택한 shelf", "상위 폴더로", "{category.skillCount} items"],
  },
  {
    file: "src/components/context/context-detail-client.tsx",
    banned: [
      "Opening context…",
      "Context not found.",
      "No project",
      "Context Reading Room",
      "Copy Content",
      "Copy Restore Prompt",
      "Confirm Archive",
      "Archive this context?",
      "Markdown Preview",
      "Retrieved Chunks",
      "Untitled",
      "Loading chunks…",
      "Recall Stats",
      "최근 조회/사용",
      ">Warnings",
      "No warnings recorded.",
    ],
  },
];

const failures = [];
for (const check of checks) {
  const source = readFileSync(join(root, check.file), "utf8");
  for (const banned of check.banned) {
    if (source.includes(banned)) {
      failures.push(`${check.file}: hardcoded visible copy remains: ${banned}`);
    }
  }
}

if (failures.length > 0) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log("i18n visible-copy contract passed");
