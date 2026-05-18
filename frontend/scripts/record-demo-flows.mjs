import { mkdirSync, renameSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "@playwright/test";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(scriptDir, "..", "..");
const recordingDir = join(repoRoot, "docs", "assets", "demo", "recordings");
const tempDir = join(recordingDir, ".tmp");

const frontendUrl = process.env.ALEXANDRIA_DEMO_FRONTEND_URL ?? "http://127.0.0.1:3000";
const demoQuery = process.env.ALEXANDRIA_DEMO_QUERY ?? "alexandria-hermes-demo";
const chatPrompt =
  process.env.ALEXANDRIA_DEMO_CHAT_PROMPT ??
  "alexandria-hermes-demo 관련 항목 몇 개야? 대표 목록 보여줘";

function routeUrl(pathname) {
  const url = new URL(pathname, frontendUrl);
  return url.toString();
}

async function fillFirstVisible(page, selector, value) {
  const target = page.locator(selector).first();
  await target.waitFor({ state: "visible", timeout: 10_000 });
  await target.fill(value);
}

async function clickFirstVisible(page, selectors) {
  for (const selector of selectors) {
    const target = page.locator(selector).first();
    try {
      await target.waitFor({ state: "visible", timeout: 2_000 });
      await target.click();
      return;
    } catch {
      // Try the next selector. Demo pages intentionally avoid test-only selectors.
    }
  }
}

async function pressEnterAfterFilter(page) {
  await page.keyboard.press("Enter");
  await page.waitForLoadState("networkidle").catch(() => undefined);
  await page.waitForTimeout(1_000);
}

async function selectDirectSearchMode(page) {
  const select = page.locator("select").first();
  try {
    await select.waitFor({ state: "visible", timeout: 2_000 });
    await select.selectOption("DIRECT_SEARCH");
  } catch {
    // The current UI may default to the desired mode or render custom controls.
  }
}

async function recordFlow(browser, flow) {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    recordVideo: {
      dir: tempDir,
      size: { width: 1440, height: 1000 },
    },
  });
  const page = await context.newPage();
  await page.goto(routeUrl(flow.path), { waitUntil: "networkidle" });
  await page.waitForTimeout(1_000);
  await flow.steps(page);
  await page.waitForTimeout(1_500);
  const video = page.video();
  await context.close();
  const sourcePath = await video.path();
  const targetPath = join(recordingDir, `${flow.name}.webm`);
  renameSync(sourcePath, targetPath);
  console.log(`${flow.name}: ${targetPath}`);
}

const flows = [
  {
    name: "context-vault-flow",
    path: "/contexts",
    steps: async (page) => {
      await fillFirstVisible(page, "input", demoQuery);
      await pressEnterAfterFilter(page);
    },
  },
  {
    name: "memory-compacts-flow",
    path: "/memory-compacts",
    steps: async (page) => {
      await fillFirstVisible(page, "input", demoQuery);
      await pressEnterAfterFilter(page);
    },
  },
  {
    name: "rag-inspector-flow",
    path: "/rag-inspector",
    steps: async (page) => {
      await fillFirstVisible(page, "textarea, input", "populated OSS screenshots Alexandria-Hermes demo");
      await clickFirstVisible(page, [
        "button:has-text('Run')",
        "button:has-text('Search')",
        "button:has-text('실행')",
        "button:has-text('검색')",
        "button[type='submit']",
      ]);
      await page.waitForLoadState("networkidle").catch(() => undefined);
      await page.waitForTimeout(2_000);
    },
  },
  {
    name: "librarian-chat-flow",
    path: "/librarian/chat",
    steps: async (page) => {
      await selectDirectSearchMode(page);
      await fillFirstVisible(page, "textarea, input", chatPrompt);
      await clickFirstVisible(page, [
        "button[type='submit']",
        "button:has-text('Send')",
        "button:has-text('Ask')",
        "button:has-text('질문')",
        "button:has-text('전송')",
      ]);
      await page.waitForLoadState("networkidle").catch(() => undefined);
      await page.waitForTimeout(3_000);
    },
  },
];

mkdirSync(recordingDir, { recursive: true });
rmSync(tempDir, { recursive: true, force: true });
mkdirSync(tempDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
try {
  for (const flow of flows) {
    await recordFlow(browser, flow);
  }
} finally {
  await browser.close();
  rmSync(tempDir, { recursive: true, force: true });
}
