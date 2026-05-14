import { rmSync } from "node:fs";
import { join } from "node:path";

const root = new URL("..", import.meta.url).pathname;
const webpackCachePath = join(root, ".next", "cache", "webpack");

try {
  rmSync(webpackCachePath, { recursive: true, force: true });
  console.log("next webpack cache cleaned");
} catch (error) {
  console.error(`failed to clean next webpack cache: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
}
