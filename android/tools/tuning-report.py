#!/usr/bin/env python3
"""Compare two native playback logcats (baseline vs tuned) and write a report.

Plan: docs/plans/2026-10-31-cast1-armv7-build-tuning.md

Usage:
  tuning-report.py --baseline LOGCAT --tuned LOGCAT --out DIR [--title TEXT]
                   [--skip-windows N]

Each logcat is read for BJG_TV_METRIC `playback_window` records emitted by the
native engine for the frozen mandel-display ROM. Windows with emu_fps == 0 are
ignored (the unpaced verification burst). The first --skip-windows paced windows
are dropped as warm-up. Writes DIR/summary.json and DIR/core-ms.svg.
"""
import argparse
import json
import re
import statistics
import sys
from pathlib import Path

WINDOW = re.compile(r'\{"event":"playback_window".*?\}')


def windows(path, skip):
    text = Path(path).read_text(errors="replace")
    rows = []
    for m in WINDOW.finditer(text):
        try:
            r = json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
        if r.get("engine") == "native" and r.get("emu_fps", 0) > 0:
            rows.append(r)
    return rows[skip:]


def pct(values, p):
    s = sorted(values)
    if not s:
        return float("nan")
    k = (len(s) - 1) * p / 100.0
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def summarize(rows):
    core = [r["core_mean_ms"] for r in rows]
    fps = [r["emu_fps"] for r in rows]
    p95 = [r["core_p95_ms"] for r in rows]
    return {
        "windows": len(rows),
        "first_rom_frame": rows[0]["rom_frames"] if rows else None,
        "last_rom_frame": rows[-1]["rom_frames"] if rows else None,
        "core_mean_ms": {
            "median": statistics.median(core), "mean": statistics.fmean(core),
            "p05": pct(core, 5), "p95": pct(core, 95),
            "min": min(core), "max": max(core)},
        "core_p95_ms_median": statistics.median(p95),
        "emu_fps": {
            "median": statistics.median(fps), "mean": statistics.fmean(fps),
            "p05": pct(fps, 5), "p95": pct(fps, 95),
            "min": min(fps), "max": max(fps)},
        "series_core_mean_ms": core,
    }


def svg(base, tuned, title, path):
    w, h, ml, mr, mt, mb = 760, 360, 70, 30, 50, 60
    top = max(max(base["series_core_mean_ms"]), max(tuned["series_core_mean_ms"]), 16.7) * 1.1
    px = lambda v: mt + (h - mt - mb) * (1 - v / top)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
           f'font-family="system-ui,sans-serif" font-size="12">',
           f'<rect width="{w}" height="{h}" fill="#fff"/>',
           f'<text x="{ml}" y="24" font-size="15" font-weight="600">{title}</text>',
           f'<text x="{ml}" y="40" fill="#555">Core ms per emulated frame, one point per 1 s playback window (lower is faster)</text>']
    for t in range(0, int(top) + 1, 10):
        y = px(t)
        out.append(f'<line x1="{ml}" x2="{w-mr}" y1="{y:.1f}" y2="{y:.1f}" stroke="#e5e5e5"/>')
        out.append(f'<text x="{ml-8}" y="{y+4:.1f}" text-anchor="end" fill="#555">{t}</text>')
    y60 = px(1000 / 60.0988)
    out.append(f'<line x1="{ml}" x2="{w-mr}" y1="{y60:.1f}" y2="{y60:.1f}" stroke="#b42318" stroke-dasharray="5 4"/>')
    out.append(f'<text x="{w-mr}" y="{y60-5:.1f}" text-anchor="end" fill="#b42318">16.6 ms = 60.1 FPS budget</text>')
    for series, color, label in ((base, "#6b7280", "baseline (ARMv7-A, no LTO, sinc)"),
                                 (tuned, "#0b6bcb", "tuned (ARMv8 AArch32, thin LTO, linear)")):
        pts = series["series_core_mean_ms"]
        n = max(len(pts) - 1, 1)
        path_d = " ".join(("M" if i == 0 else "L") + f"{ml + (w-ml-mr)*i/n:.1f},{px(v):.1f}" for i, v in enumerate(pts))
        out.append(f'<path d="{path_d}" fill="none" stroke="{color}" stroke-width="1.6"/>')
        med = series["core_mean_ms"]["median"]
        out.append(f'<line x1="{ml}" x2="{w-mr}" y1="{px(med):.1f}" y2="{px(med):.1f}" stroke="{color}" stroke-width="1" stroke-dasharray="2 3"/>')
        out.append(f'<text x="{ml+6}" y="{px(med)-4:.1f}" fill="{color}">median {med:.1f} ms</text>')
    ly = h - 28
    out.append(f'<rect x="{ml}" y="{ly-9}" width="14" height="3" fill="#6b7280"/><text x="{ml+20}" y="{ly}" >baseline (ARMv7-A, no LTO, sinc)</text>')
    out.append(f'<rect x="{ml+260}" y="{ly-9}" width="14" height="3" fill="#0b6bcb"/><text x="{ml+280}" y="{ly}">tuned (ARMv8 AArch32, thin LTO, linear)</text>')
    out.append(f'<text x="{(ml+w-mr)/2}" y="{h-8}" text-anchor="middle" fill="#555">playback window index</text>')
    out.append('</svg>')
    Path(path).write_text("\n".join(out))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--tuned", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="Cast1 native core time")
    ap.add_argument("--skip-windows", type=int, default=3)
    a = ap.parse_args()
    b = summarize(windows(a.baseline, a.skip_windows))
    t = summarize(windows(a.tuned, a.skip_windows))
    if not b["windows"] or not t["windows"]:
        sys.exit("no paced native playback_window records in one of the logcats")
    speedup = b["core_mean_ms"]["median"] / t["core_mean_ms"]["median"]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(
        {"baseline": {k: v for k, v in b.items() if k != "series_core_mean_ms"},
         "tuned": {k: v for k, v in t.items() if k != "series_core_mean_ms"},
         "median_core_speedup": speedup}, indent=2))
    svg(b, t, a.title, out / "core-ms.svg")
    print(f"baseline: {b['windows']} windows, median {b['core_mean_ms']['median']:.2f} ms, {b['emu_fps']['median']:.2f} FPS")
    print(f"tuned:    {t['windows']} windows, median {t['core_mean_ms']['median']:.2f} ms, {t['emu_fps']['median']:.2f} FPS")
    print(f"median core-time speedup: {speedup:.3f}x")


if __name__ == "__main__":
    main()
