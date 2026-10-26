#!/usr/bin/env node
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { basename, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const CSV_FIELDS = [
  "t_ms", "rom_run", "frames", "rom_frames", "sample_frames", "window_ms", "target_hz",
  "core_mean_ms", "core_p95_ms", "core_max_ms", "canvas_callbacks",
  "canvas_submit_mean_ms", "canvas_submit_p95_ms", "canvas_submit_max_ms",
  "raf_interval_p95_ms", "raf_interval_max_ms", "emulation_backlog_frames", "peak_backlog_frames"
];

export function parseMetrics(text) {
  const events = [];
  for (const line of text.split(/\r?\n/)) {
    const marker = line.indexOf("BJG_TV_METRIC");
    if (marker < 0) continue;
    let raw = line.slice(marker + "BJG_TV_METRIC".length).trim();
    if (raw.startsWith(":")) raw = raw.slice(1).trim();
    try {
      const item = JSON.parse(raw);
      if (item && typeof item.event === "string") events.push(item);
    } catch {
      // Ignore unrelated/truncated log lines; retain every valid metric record.
    }
  }
  return events;
}

function csvCell(value) {
  if (value === undefined || value === null) return "";
  const text = String(value);
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

export function playbackCsv(events) {
  const rows = events.filter(event => event.event === "playback_window");
  return [CSV_FIELDS.join(","), ...rows.map(row => CSV_FIELDS.map(field => csvCell(row[field])).join(","))].join("\n") + "\n";
}

function quantile(values, q) {
  if (!values.length) return null;
  const sorted = values.slice().sort((a, b) => a - b);
  if (q <= 0) return sorted[0];
  if (q >= 1) return sorted[sorted.length - 1];
  return sorted[Math.min(sorted.length - 1, Math.ceil(sorted.length * q) - 1)];
}

function fmt(value) {
  return value === null ? "n/a" : Number(value).toFixed(3);
}

export function summaryMarkdown(events, inputName) {
  const rows = events.filter(event => event.event === "playback_window");
  const columns = [
    ["Core mean per 60-frame window (ms)", "core_mean_ms"],
    ["Core p95 per 60-frame window (ms)", "core_p95_ms"],
    ["Canvas submission mean per callback (ms)", "canvas_submit_mean_ms"],
    ["Canvas submission p95 per callback (ms)", "canvas_submit_p95_ms"],
    ["WebView RAF interval p95 (ms)", "raf_interval_p95_ms"],
    ["Peak emulation backlog (frames)", "peak_backlog_frames"]
  ];
  const lines = [
    `# Phase 1 WebView metrics — ${inputName}`, "",
    `Parsed ${events.length} structured events and ${rows.length} rolling playback windows.`,
    "Intervals are app-side observations. RAF intervals are callback spacing, not compositor presentation.",
    "Window quantiles summarize window-level values; they are not per-frame distributions.", "",
    "| Measure | Windows | Min | Median | p95 | p99 | Max |", "|---|---:|---:|---:|---:|---:|---:|"
  ];
  for (const [label, key] of columns) {
    const values = rows.map(row => Number(row[key])).filter(Number.isFinite);
    lines.push(`| ${label} | ${values.length} | ${fmt(quantile(values, 0))} | ${fmt(quantile(values, 0.5))} | ${fmt(quantile(values, 0.95))} | ${fmt(quantile(values, 0.99))} | ${fmt(quantile(values, 1))} |`);
  }
  lines.push("", "## Event counts", "", "| Event | Count |", "|---|---:|");
  const counts = new Map();
  for (const event of events) counts.set(event.event, (counts.get(event.event) || 0) + 1);
  for (const [name, count] of [...counts].sort(([a], [b]) => a.localeCompare(b))) lines.push(`| ${name} | ${count} |`);
  lines.push("");
  return lines.join("\n");
}

export function pacingSvg(events, title = "Phase 1 WebView playback") {
  const rows = events.filter(event => event.event === "playback_window");
  const width = 1120, height = 640, left = 90, right = 34, top = 86, bottom = 92;
  const plotW = width - left - right, plotH = height - top - bottom;
  const series = [
    { key: "core_mean_ms", name: "Core step mean", color: "#42b8ff" },
    { key: "canvas_submit_mean_ms", name: "Canvas submission mean", color: "#ffb34d" },
    { key: "raf_interval_p95_ms", name: "RAF callback interval p95", color: "#b69cff" }
  ];
  const vals = rows.flatMap(row => series.map(item => Number(row[item.key])).filter(Number.isFinite));
  const xvals = rows.map(row => Number(row.rom_frames)).filter(Number.isFinite);
  const maxX = Math.max(1, ...xvals), maxY = Math.max(1, ...vals) * 1.12;
  const x = value => left + value / maxX * plotW;
  const y = value => top + plotH - value / maxY * plotH;
  const parts = [
    `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`,
    `<rect width="100%" height="100%" rx="18" fill="#0b1220"/>`,
    `<text x="${left}" y="42" fill="#f0f5fb" font-family="Arial,sans-serif" font-size="24" font-weight="700">${escapeXml(title)}</text>`,
    `<text x="${left}" y="65" fill="#9fb0c5" font-family="Arial,sans-serif" font-size="14">App-side intervals in milliseconds · RAF is not display presentation</text>`
  ];
  for (let tick = 0; tick <= 5; tick++) {
    const value = maxY * tick / 5, yy = y(value);
    parts.push(`<path d="M${left} ${yy}H${width - right}" stroke="#26354a"/>`);
    parts.push(`<text x="${left - 12}" y="${yy + 5}" text-anchor="end" fill="#9fb0c5" font-family="Arial,sans-serif" font-size="13">${value.toFixed(1)}</text>`);
  }
  parts.push(`<path d="M${left} ${top}V${top + plotH}H${width - right}" fill="none" stroke="#7d8da3"/>`);
  if (rows.length) {
    for (const item of series) {
      const points = rows.map(row => [Number(row.rom_frames), Number(row[item.key])]).filter(point => point.every(Number.isFinite));
      const d = points.map(([frame, value], i) => `${i ? "L" : "M"}${x(frame).toFixed(1)} ${y(value).toFixed(1)}`).join(" ");
      parts.push(`<path d="${d}" fill="none" stroke="${item.color}" stroke-width="3"/>`);
    }
    const ref = events.find(event => event.event === "reference_ready" && Number.isFinite(Number(event.frame)));
    if (ref) {
      const xx = x(Number(ref.frame));
      parts.push(`<path d="M${xx} ${top}V${top + plotH}" stroke="#79df9b" stroke-dasharray="7 6"/>`);
      parts.push(`<text x="${xx + 7}" y="${top + 18}" fill="#79df9b" font-family="Arial,sans-serif" font-size="13">WRAM oracle ready</text>`);
    }
  } else {
    parts.push(`<text x="${left + plotW / 2}" y="${top + plotH / 2}" text-anchor="middle" fill="#aebbd0" font-family="Arial,sans-serif" font-size="20">No playback_window records in input</text>`);
  }
  parts.push(`<text x="${left + plotW / 2}" y="${height - 42}" text-anchor="middle" fill="#b5c3d7" font-family="Arial,sans-serif" font-size="15">Emulated frame count</text>`);
  parts.push(`<text transform="translate(26 ${top + plotH / 2}) rotate(-90)" text-anchor="middle" fill="#b5c3d7" font-family="Arial,sans-serif" font-size="15">Milliseconds</text>`);
  series.forEach((item, i) => {
    const xx = left + i * 270;
    parts.push(`<path d="M${xx} ${height - 18}h28" stroke="${item.color}" stroke-width="4"/>`);
    parts.push(`<text x="${xx + 36}" y="${height - 13}" fill="#b5c3d7" font-family="Arial,sans-serif" font-size="14">${escapeXml(item.name)}</text>`);
  });
  parts.push("</svg>");
  return parts.join("\n");
}

function escapeXml(value) {
  return String(value).replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&apos;" })[char]);
}

export async function generateReport(logText, inputName, outputDir) {
  const events = parseMetrics(logText);
  if (!events.length) throw new Error("no BJG_TV_METRIC records found in input");
  const out = resolve(outputDir);
  await mkdir(out, { recursive: true });
  await writeFile(resolve(out, "events.jsonl"), events.map(event => JSON.stringify(event)).join("\n") + "\n");
  await writeFile(resolve(out, "playback.csv"), playbackCsv(events));
  await writeFile(resolve(out, "summary.md"), summaryMarkdown(events, inputName));
  await writeFile(resolve(out, "frame-pacing.svg"), pacingSvg(events, `Phase 1 playback — ${inputName}`));
  return events.length;
}

async function main(args) {
  if (args.length !== 2 || args.includes("--help")) {
    throw new Error("Usage: node metrics-report.mjs <coordinator-logcat.txt> <output-directory>");
  }
  const input = resolve(args[0]);
  const count = await generateReport(await readFile(input, "utf8"), basename(input), args[1]);
  console.log(`Wrote Phase 1 metrics from ${count} events to ${resolve(args[1])}`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main(process.argv.slice(2)).catch(error => { console.error(error.message); process.exitCode = 2; });
}
