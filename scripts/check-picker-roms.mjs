#!/usr/bin/env node
// Every picker button's data-rom must be a ROM the manifest knows: a button for
// a ROM that was dropped (see 85de645) 404s when clicked.
// Usage: check-picker-roms.mjs [index.html] [manifest.json]
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "web");
const [indexPath = join(root, "index.html"), manifestPath = join(root, "roms", "manifest.json")] = process.argv.slice(2);
if (indexPath === "-h" || indexPath === "--help") {
  console.log("Usage: check-picker-roms.mjs [index.html] [manifest.json]");
  process.exit(0);
}
const known = new Set(JSON.parse(readFileSync(manifestPath, "utf8")).roms.map((r) => r.id));
const used = [...readFileSync(indexPath, "utf8").matchAll(/<button[^>]*\bdata-rom="([^"]+)"/g)].map((m) => m[1]);
const missing = used.filter((slug) => !known.has(slug));
if (missing.length) {
  console.error(`picker buttons without a manifest entry: ${missing.join(", ")}`);
  process.exit(1);
}
console.log(`picker ok: ${used.join(", ")}`);
