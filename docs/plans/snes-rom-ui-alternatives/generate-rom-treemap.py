#!/usr/bin/env python3
"""Generate the design packet's size-accurate ROM treemap SVG."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BUILD = ROOT.parent / "llvm-mos-65816" / "build"
CONTENT = ROOT.parent / "biohack.net" / "src" / "content" / "snes"
OUT = Path(__file__).with_name("rom-treemap.svg")
W, H = 1100.0, 505.0
COLORS = {
    "other": "#38506b", "fractals": "#5070a0", "physics": "#6877ae",
    "cellular": "#3c8a80", "motion": "#88734b", "algorithms": "#4e7d96",
    "rendering": "#7966a2", "video": "#b15f64", "signals": "#4a8b68",
    "bignums": "#6a8652", "ciphers": "#96714f", "classics": "#ac6848",
    "cartridge": "#756c83",
}
LABELS = {
    "other": "Other builds", "fractals": "Fractals", "physics": "Physics & Simulation",
    "cellular": "Cellular Automata", "motion": "Motion & Curves", "algorithms": "Algorithms & Data",
    "rendering": "Rendering & Graphics", "video": "Video Playback", "signals": "Signals & Audio",
    "bignums": "Big Numbers", "ciphers": "Ciphers & Bit Tricks", "classics": "Games & Classics",
    "cartridge": "Cartridge & Mapping Tests",
}

metadata = {}
for file in CONTENT.glob("*.json"):
    item = json.loads(file.read_text())
    metadata[item["slug"] + ".sfc"] = (item["category"], item["title"])

groups = {}
for rom in BUILD.glob("*.sfc"):
    category, title = metadata.get(rom.name, ("other", rom.stem.replace("-", " ").replace("_", " ").title()))
    groups.setdefault(category, []).append({"name": rom.name, "title": title, "size": rom.stat().st_size})
    groups[category][-1]["selected"] = rom.name == "apollo-daylight.sfc"


def squarify(items, x, y, w, h):
    """Approximate a classic squarified treemap with each area proportional to size."""
    total = sum(item["weight"] for item in items)
    if total <= 0 or w <= 0 or h <= 0:
        return []
    scaled = [{**item, "area": item["weight"] * w * h / total} for item in items]
    out, row, left = [], [], scaled[:]

    def worst(values, side):
        if not values:
            return float("inf")
        area = sum(v["area"] for v in values)
        lo, hi = min(v["area"] for v in values), max(v["area"] for v in values)
        if not lo or not area:
            return float("inf")
        return max(side * side * hi / (area * area), (area * area) / (side * side * lo))

    while left:
        side = min(w, h)
        if not row or worst(row + [left[0]], side) <= worst(row, side):
            row.append(left.pop(0))
            if left:
                continue
        row_area = sum(v["area"] for v in row)
        if w >= h:
            band = row_area / h
            cy = y
            for item in row:
                rh = item["area"] / band
                out.append((item, x, cy, band, rh))
                cy += rh
            x += band
            w -= band
        else:
            band = row_area / w
            cx = x
            for item in row:
                rw = item["area"] / band
                out.append((item, cx, y, rw, band))
                cx += rw
            y += band
            h -= band
        row = []
    return out


def text(x, y, value, size, color="#f2f5f8", weight=400):
    return f'<text x="{x:.1f}" y="{y:.1f}" fill="{color}" font-family="Arial,sans-serif" font-size="{size}" font-weight="{weight}">{html.escape(value)}</text>'


def fmt_size(n):
    return f"{n / 1048576:.1f} MiB" if n >= 1048576 else f"{n // 1024} KiB"


svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:g} {H:g}" role="img" aria-labelledby="t d">',
       '<title id="t">ROM treemap grouped by category</title><desc id="d">All generated SNES ROM files shown as rectangles with areas proportional to exact byte size.</desc>',
       '<rect width="100%" height="100%" fill="#0b1017"/>']
group_items = [{"key": k, "weight": sum(i["size"] for i in v)} for k, v in groups.items()]
group_items.sort(key=lambda g: (-g["weight"], g["key"]))
for group, gx, gy, gw, gh in squarify(group_items, 0, 0, W, H):
    key = group["key"]
    items = sorted(groups[key], key=lambda item: (-item["size"], item["name"]))
    ix, iy, iw, ih = gx, gy, gw, gh
    if gw > 95 and gh > 38:
        svg.append(f'<rect x="{gx:.2f}" y="{gy:.2f}" width="{gw:.2f}" height="{gh:.2f}" fill="none" stroke="#101720" stroke-width="3"/>')
        svg.append(f'<rect x="{gx + 4:.2f}" y="{gy + 2:.2f}" width="156" height="16" rx="3" fill="#0b1017" fill-opacity=".82"/>')
        svg.append(text(gx + 7, gy + 13, f'{LABELS[key]} · {len(items)}', 10, "#f6f8fb", 600))
    for item, x, y, w, h in squarify([{"data": it, "weight": it["size"]} for it in items], ix, iy, iw, ih):
        rom = item["data"]
        fill = COLORS[key]
        stroke = "#ffffff" if rom["selected"] else "#111822"
        stroke_width = "3" if rom["selected"] else "1"
        svg.append(f'<g><title>{html.escape(rom["title"])} · {html.escape(rom["name"])} · {fmt_size(rom["size"])}</title><rect x="{x:.2f}" y="{y:.2f}" width="{max(0,w):.2f}" height="{max(0,h):.2f}" rx="1.5" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>')
        if w > 80 and h > 30:
            svg.append(text(x + 6, y + 16, rom["title"][:28], 10 if w < 150 else 12, "#fff", 600))
            if h > 49:
                svg.append(text(x + 6, y + 32, fmt_size(rom["size"]), 9, "#d8e0ea"))
        svg.append('</g>')
svg.append('</svg>')
OUT.write_text("\n".join(svg))
print(f"{OUT}: {sum(len(x) for x in groups.values())} ROM tiles, {OUT.stat().st_size // 1024} KiB")
