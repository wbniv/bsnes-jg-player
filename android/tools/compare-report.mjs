#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../docs/performance/2026-10-26/wasm-vs-native');
const data = JSON.parse(fs.readFileSync(path.join(root, 'runs.json'), 'utf8'));
if (!Array.isArray(data.runs)) throw new Error('runs.json must contain a runs array');
if (!fs.existsSync(path.join(root, 'comparison.md'))) throw new Error('comparison.md is missing');
for (const run of data.runs) {
  if (!run.device || !run.engine || !run.job || !run.status) {
    throw new Error(`Run record is missing provenance: ${JSON.stringify(run)}`);
  }
}
console.log(`Validated ${data.runs.length} evidence-linked runs. The curated report and charts are in ${root}.`);
