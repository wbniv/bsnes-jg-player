#!/usr/bin/env python3
"""Stage the published SNES ROM catalog and deterministic in-game card art."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
COLLECTION = ROOT.parent / "biohack.net" / "src" / "content" / "snes"
BUILDS = ROOT.parent / "llvm-mos-65816" / "build"
PUBLISHED = ROOT.parent / "biohack.net" / "public" / "play" / "roms"
JGXCHECK = BUILDS / "jgxcheck"
DATABASE = ROOT / "vendor" / "bsnes-jg" / "Database"
FRAME_BUDGET = 600
CATEGORY_LABELS = {
    "fractals": "Fractals", "physics": "Physics & Simulation",
    "cellular": "Cellular Automata", "motion": "Motion & Curves",
    "algorithms": "Algorithms & Data", "rendering": "Rendering & Graphics",
    "video": "Video Playback", "signals": "Signals & Audio",
    "bignums": "Big Numbers", "ciphers": "Ciphers & Bit Tricks",
    "classics": "Games & Classics", "cartridge": "Cartridge & Mapping Tests",
}
CATEGORY_COLOURS = {
    "fractals": (36, 79, 132), "physics": (31, 103, 103),
    "cellular": (72, 104, 52), "motion": (120, 77, 45),
    "algorithms": (54, 76, 119), "rendering": (100, 56, 109),
    "video": (135, 60, 48), "signals": (55, 93, 116),
    "bignums": (114, 79, 34), "ciphers": (65, 78, 99),
    "classics": (137, 62, 79), "cartridge": (63, 96, 68),
}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def title_card(title, category, target):
    im = Image.new("RGB", (256, 224), (8, 12, 20))
    draw = ImageDraw.Draw(im)
    base = CATEGORY_COLOURS.get(category, (55, 75, 105))
    draw.rectangle((0, 0, 255, 7), fill=base)
    draw.rectangle((0, 216, 255, 223), fill=base)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 17)
    except OSError:
        font = ImageFont.load_default()
    printable = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii") or title
    words, lines, line = printable.split(), [], ""
    for word in words:
        trial = (line + " " + word).strip()
        if line and draw.textbbox((0, 0), trial, font=font)[2] > 224:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    lines = lines[:4]
    line_h = 24
    y = (224 - len(lines) * line_h) // 2
    for text in lines:
        box = draw.textbbox((0, 0), text, font=font)
        draw.text(((256 - (box[2] - box[0])) // 2, y), text, font=font, fill=(239, 245, 252))
        y += line_h
    im.save(target, format="PNG", optimize=True)


def capture_card(rom_path, record, output_path):
    frame = int(record.get("cardFrame", FRAME_BUDGET))
    if not 1 <= frame <= 100000:
        raise SystemExit(f"Invalid cardFrame for {record['slug']}: {frame}")
    env = os.environ.copy()
    env["JGX_ENTROPY"] = "0"
    result = subprocess.run(
        [str(JGXCHECK), str(rom_path), str(DATABASE), "0", "1", "0", str(frame), str(output_path)],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env=env, check=False,
    )
    if not output_path.is_file():
        detail = result.stderr.decode("utf-8", "replace")[-1000:]
        raise SystemExit(f"Could not capture {record['slug']} at frame {frame}: {detail}")
    with Image.open(output_path) as source:
        im = source.convert("RGB")
        if im.size != (256, 224):
            im = im.resize((256, 224), Image.Resampling.NEAREST)
        colours = im.getcolors(maxcolors=1_000_000)
        dominant = max((count for count, _ in colours), default=0) / (256 * 224) if colours else 0
        blank = dominant >= 0.90
        if blank:
            title_card(record["title"], record["category"], output_path)
            with Image.open(output_path) as fallback:
                im = fallback.convert("RGB")
        palette = im.getcolors(maxcolors=257)
        if palette and len(palette) <= 256:
            im.quantize(colors=max(1, len(palette)), method=Image.Quantize.FASTOCTREE,
                        dither=Image.Dither.NONE).save(output_path, format="PNG", optimize=True)
        else:
            im.save(output_path, format="PNG", optimize=True)
    return frame, dominant, blank


def validate_existing(output):
    catalog_path = output / "library.json"
    if not catalog_path.is_file():
        raise SystemExit(f"No staged catalog at {catalog_path}; run without --validate-only to stage it")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    records = catalog.get("roms", [])
    source_paths = {p.stem: p for p in COLLECTION.glob("*.json")}
    if len(records) != len(source_paths) or {r.get("slug") for r in records} != set(source_paths):
        raise SystemExit("Staged catalog membership differs from the published source; refresh the library")
    for record in records:
        slug = record["slug"]
        source = BUILDS / f"{slug}.sfc"
        if not source.is_file():
            source = PUBLISHED / f"{slug}.sfc"
        rom = output / "roms" / record["filename"]
        card = output / record["card"]
        if not source.is_file() or not rom.is_file() or digest(source) != record["romSha256"] or digest(rom) != record["romSha256"]:
            raise SystemExit(f"Staged ROM differs from its published source: {slug}; refresh the library")
        if rom.stat().st_size != record["size"]:
            raise SystemExit(f"Staged ROM size mismatch: {slug}")
        if not card.is_file() or digest(card) != record["cardSha256"]:
            raise SystemExit(f"Staged card differs from its catalog hash: {slug}; refresh the library")
    print(f"Validated {len(records)} staged catalog records, ROMs, source hashes, and card hashes")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--check", action="store_true", help="validate staged hashes and report blank-frame fallbacks")
    parser.add_argument("--validate-only", action="store_true", help="verify existing staged files without recapturing card art")
    args = parser.parse_args()
    if not COLLECTION.is_dir() or not BUILDS.is_dir() or not PUBLISHED.is_dir() or not JGXCHECK.is_file() or not DATABASE.is_dir():
        raise SystemExit("Expected biohack.net SNES records, ROM inputs, jgxcheck, and bsnes-jg Database")

    output = args.output.resolve()
    if args.validate_only:
        validate_existing(output)
        return
    if args.check and (output / "library.json").is_file():
        catalog = json.loads((output / "library.json").read_text(encoding="utf-8"))
        records = catalog.get("roms", [])
        expected = {json.loads(path.read_text(encoding="utf-8"))["slug"] for path in COLLECTION.glob("*.json")}
        if len(records) != len(expected) or {item["slug"] for item in records} != expected:
            raise SystemExit("Staged catalog does not match the published SNES content records")
        for record in records:
            slug = record["slug"]
            rom_file = output / "roms" / f"{slug}.sfc"
            card_file = output / "cards" / f"{slug}.png"
            source = BUILDS / f"{slug}.sfc"
            if not source.is_file():
                source = PUBLISHED / f"{slug}.sfc"
            if not source.is_file() or not rom_file.is_file() or digest(source) != record["romSha256"] or digest(rom_file) != record["romSha256"]:
                raise SystemExit(f"ROM staging check failed: {slug}")
            if not card_file.is_file() or digest(card_file) != record["cardSha256"]:
                raise SystemExit(f"Card staging check failed: {slug}")
        if {p.stem for p in (output / "roms").glob("*.sfc")} != expected or {p.stem for p in (output / "cards").glob("*.png")} != expected:
            raise SystemExit("Staging directory has missing or extra ROM/card files")
        print(f"Check passed: {len(records)} catalog records, exact ROM bytes, and card hashes")
        raise SystemExit(0)
    output.mkdir(parents=True, exist_ok=True)
    rom_dir, card_dir = output / "roms", output / "cards"
    for directory in (rom_dir, card_dir):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True)
    records, seen = [], set()
    blanks = []
    total_bytes = 0
    jobs = []
    for path in COLLECTION.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        slug = data["slug"]
        if slug in seen or Path(slug).name != slug or "/" in slug or "\\" in slug:
            raise SystemExit(f"Duplicate or unsafe ROM slug: {slug}")
        seen.add(slug)
        source = BUILDS / f"{slug}.sfc"
        if not source.is_file():
            source = PUBLISHED / f"{slug}.sfc"
        if not source.is_file():
            raise SystemExit(f"Published ROM has no build or published asset: {slug}.sfc")
        category = data["category"]
        record = {
            "slug": slug, "filename": f"{slug}.sfc", "title": data["title"],
            "desc": data.get("desc", ""), "keys": data.get("keys", ""),
            "compilerBug": data.get("compilerBug", False),
            "interactive": not data.get("keys", "").startswith(("Self-running", "No controls")),
            "category": category, "categoryLabel": CATEGORY_LABELS.get(category, category),
            "displayMode": data.get("displayMode"), "order": data["order"],
            "size": source.stat().st_size,
            "source": "llvm-mos-65816/build" if source.parent == BUILDS else "biohack.net published ROM",
        }
        shutil.copyfile(source, rom_dir / record["filename"])
        card_path = card_dir / f"{slug}.png"
        jobs.append((record, data, source, card_path))
        total_bytes += record["size"]
    # Captures are independent. Four parallel headless core runs keep the
    # 600-frame deterministic capture pass practical without overloading TVs.
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(capture_card, source, data, card_path): (record, source)
                   for record, data, source, card_path in jobs}
        for future in as_completed(futures):
            record, source = futures[future]
            frame, dominant, blank = future.result()
            # Copy after capture as well, ensuring exact source bytes even if
            # the emulator writes cartridge state beside its input.
            shutil.copyfile(source, rom_dir / record["filename"])
            card_path = card_dir / f"{record['slug']}.png"
            record["card"] = f"cards/{record['slug']}.png"
            record["cardSha256"] = digest(card_path)
            record["cardFrame"] = frame
            record["cardFallback"] = blank
            record["romSha256"] = digest(rom_dir / record["filename"])
            if blank:
                blanks.append((record["slug"], f"{dominant:.1%}"))
            records.append(record)
    records.sort(key=lambda item: (-item["order"], item["slug"]))
    if not records:
        raise SystemExit("No published SNES ROMs found")
    catalog = {"schemaVersion": 1, "source": "biohack.net SNES published catalog", "roms": records}
    catalog_path = output / "library.json"
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Staged {len(records)} published ROMs ({total_bytes:,} raw bytes) and {len(records)} deterministic cards into {output}")
    if blanks:
        print("Captured frames >=90% one colour; generated title-card fallbacks:")
        for slug, percent in blanks:
            print(f"  {slug}: {percent}")
    if args.check:
        check_data = json.loads(catalog_path.read_text(encoding="utf-8"))
        if len(check_data["roms"]) != len(records):
            raise SystemExit("Catalog record count changed during staging")
        for record in records:
            rom_file = rom_dir / record["filename"]
            card_file = output / record["card"]
            if not rom_file.is_file() or rom_file.stat().st_size != record["size"] or digest(rom_file) != record["romSha256"]:
                raise SystemExit(f"ROM staging check failed: {record['slug']}")
            if not card_file.is_file() or digest(card_file) != record["cardSha256"]:
                raise SystemExit(f"Card staging check failed: {record['slug']}")
        print(f"Check passed: {len(records)} catalog records, ROMs, and card hashes")


if __name__ == "__main__":
    main()
