import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const root = new URL("..", import.meta.url).pathname;
const lockPath = join(root, "package-lock.json");

const compromisedVersions = new Map([
  ["@mistralai/mistralai", new Set(["2.2.3", "2.2.4"])],
  ["@opensearch-project/opensearch", new Set(["3.6.2"])],
  ["@tanstack/router-utils", new Set(["1.161.11", "1.161.14"])],
  ["@tanstack/router-core", new Set(["1.169.5", "1.169.8"])],
  ["@tanstack/react-router", new Set(["1.169.5", "1.169.8"])],
  ["@tanstack/react-router-devtools", new Set(["1.166.16", "1.166.19"])],
  ["@tanstack/router-cli", new Set(["1.166.46", "1.166.49"])],
  ["@tanstack/router-generator", new Set(["1.166.45", "1.166.48"])],
  ["@tanstack/router-plugin", new Set(["1.167.38", "1.167.41"])],
  ["@tanstack/router-vite-plugin", new Set(["1.166.53", "1.166.56"])],
  ["@uipath/docsai-tool", new Set(["1.0.1"])],
  ["safe-action", new Set(["0.8.3", "0.8.4"])],
  ["cmux-agent-mcp", new Set(["0.1.3", "0.1.4", "0.1.5", "0.1.6", "0.1.7", "0.1.8"])],
  ["nextmove-mcp", new Set(["0.1.3", "0.1.4", "0.1.5", "0.1.7"])],
]);

const suspiciousPackageNames = new Set([
  "@tanstack/setup",
]);

const suspiciousTextMarkers = [
  "github:tanstack/router#79ac49eedf774dd4b0cfa308722bc463cfe5885c",
  "git-tanstack.com",
  "router_init.js",
  "opensearch_init.js",
  "tanstack_runner.js",
];

const suspiciousFileNames = new Set([
  "router_init.js",
  "opensearch_init.js",
  "tanstack_runner.js",
]);

function checkPackage(name, version, location, violations) {
  if (!name || !version) return;
  if (compromisedVersions.get(name)?.has(version)) {
    violations.push(`${location}: compromised package version ${name}@${version}`);
  }
  if (suspiciousPackageNames.has(name)) {
    violations.push(`${location}: suspicious package present: ${name}`);
  }
}

function checkOptionalDependencies(optionalDependencies, location, violations) {
  if (!optionalDependencies || typeof optionalDependencies !== "object") return;
  for (const [name, version] of Object.entries(optionalDependencies)) {
    if (suspiciousPackageNames.has(name)) {
      violations.push(`${location}: suspicious optional dependency ${name}@${version}`);
    }
    if (typeof version === "string" && version.includes("github:tanstack/router")) {
      violations.push(`${location}: suspicious optional dependency target ${name}@${version}`);
    }
  }
}

function checkLockfile(violations) {
  if (!existsSync(lockPath)) return;
  const raw = readFileSync(lockPath, "utf8");
  for (const marker of suspiciousTextMarkers) {
    if (raw.includes(marker)) {
      violations.push(`package-lock.json contains suspicious marker: ${marker}`);
    }
  }

  const lock = JSON.parse(raw);
  for (const [path, metadata] of Object.entries(lock.packages ?? {})) {
    if (!metadata || typeof metadata !== "object") continue;
    const inferredName = path.includes("node_modules/") ? path.split("node_modules/").at(-1) : undefined;
    const name = metadata.name ?? inferredName;
    checkPackage(name, metadata.version, path || "package root", violations);
    checkOptionalDependencies(metadata.optionalDependencies, path || "package root", violations);
  }
}

function walk(dir, violations) {
  for (const entry of readdirSync(dir)) {
    if (entry === ".next" || entry === ".git") continue;
    const path = join(dir, entry);
    const stat = statSync(path);
    if (stat.isDirectory()) {
      walk(path, violations);
      continue;
    }
    if (suspiciousFileNames.has(entry)) {
      violations.push(`suspicious payload file found: ${relative(root, path)}`);
    }
  }
}

const violations = [];
checkLockfile(violations);
walk(root, violations);

if (violations.length > 0) {
  console.error(violations.join("\n"));
  process.exit(1);
}

console.log("npm supply-chain guard ok");
