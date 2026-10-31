#!/usr/bin/env python3
"""Stage the published SNES ROM catalog and biohack.net gallery previews."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COLLECTION = ROOT.parent / "biohack.net" / "src" / "content" / "snes"
BUILDS = ROOT.parent / "llvm-mos-65816" / "build"
PUBLISHED = ROOT.parent / "biohack.net" / "public" / "play" / "roms"
PREVIEWS = ROOT.parent / "biohack.net" / "public" / "play" / "preview"
CATEGORY_LABELS = {
    "fractals": "Fractals", "physics": "Physics & Simulation",
    "cellular": "Cellular Automata", "motion": "Motion & Curves",
    "algorithms": "Algorithms & Data", "rendering": "Rendering & Graphics",
    "video": "Video Playback", "signals": "Signals & Audio",
    "bignums": "Big Numbers", "ciphers": "Ciphers & Bit Tricks",
    "classics": "Games & Classics", "cartridge": "Cartridge & Mapping Tests",
}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


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
        preview = PREVIEWS / f"{slug}.png"
        if not source.is_file() or not rom.is_file() or digest(source) != record["romSha256"] or digest(rom) != record["romSha256"]:
            raise SystemExit(f"Staged ROM differs from its published source: {slug}; refresh the library")
        if rom.stat().st_size != record["size"]:
            raise SystemExit(f"Staged ROM size mismatch: {slug}")
        if not preview.is_file() or record.get("cardSource") != f"/play/preview/{slug}.png":
            raise SystemExit(f"Published site preview mapping is missing or changed: {slug}")
        if not card.is_file() or digest(card) != record["cardSha256"] or digest(card) != digest(preview):
            raise SystemExit(f"Staged card differs from its catalog hash: {slug}; refresh the library")
    print(f"Validated {len(records)} staged catalog records, ROMs, source hashes, and card hashes")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--check", action="store_true", help="validate staged ROM and site-preview hashes")
    parser.add_argument("--validate-only", action="store_true", help="verify existing staged files without restaging")
    args = parser.parse_args()
    if not COLLECTION.is_dir() or not BUILDS.is_dir() or not PUBLISHED.is_dir() or not PREVIEWS.is_dir():
        raise SystemExit("Expected biohack.net SNES records, published previews, and llvm-mos ROM inputs")

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
            preview_file = PREVIEWS / f"{slug}.png"
            source = BUILDS / f"{slug}.sfc"
            if not source.is_file():
                source = PUBLISHED / f"{slug}.sfc"
            if not source.is_file() or not rom_file.is_file() or digest(source) != record["romSha256"] or digest(rom_file) != record["romSha256"]:
                raise SystemExit(f"ROM staging check failed: {slug}")
            if (not preview_file.is_file() or record.get("cardSource") != f"/play/preview/{slug}.png"
                    or not card_file.is_file() or digest(card_file) != record["cardSha256"]
                    or digest(card_file) != digest(preview_file)):
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
    total_bytes = 0
    expected = {json.loads(path.read_text(encoding="utf-8"))["slug"] for path in COLLECTION.glob("*.json")}
    preview_slugs = {path.stem for path in PREVIEWS.glob("*.png")}
    if missing := sorted(expected - preview_slugs):
        raise SystemExit(f"Site previews are missing for published ROMs: {missing}")
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
        card_source = PREVIEWS / f"{slug}.png"
        if not card_source.is_file():
            raise SystemExit(f"Published site preview is missing: {card_source}")
        record["card"] = f"cards/{slug}.png"
        record["cardSource"] = f"/play/preview/{slug}.png"
        record["cardSha256"] = digest(card_source)
        shutil.copyfile(card_source, card_dir / f"{slug}.png")
        shutil.copyfile(source, rom_dir / record["filename"])
        record["romSha256"] = digest(rom_dir / record["filename"])
        records.append(record)
        total_bytes += record["size"]
    records.sort(key=lambda item: (-item["order"], item["slug"]))
    if not records:
        raise SystemExit("No published SNES ROMs found")
    catalog = {"schemaVersion": 1, "source": "biohack.net SNES published catalog", "roms": records}
    catalog_path = output / "library.json"
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Staged {len(records)} published ROMs ({total_bytes:,} raw bytes) and {len(records)} site previews into {output}")
    if args.check:
        check_data = json.loads(catalog_path.read_text(encoding="utf-8"))
        if len(check_data["roms"]) != len(records):
            raise SystemExit("Catalog record count changed during staging")
        for record in records:
            rom_file = rom_dir / record["filename"]
            card_file = output / record["card"]
            if not rom_file.is_file() or rom_file.stat().st_size != record["size"] or digest(rom_file) != record["romSha256"]:
                raise SystemExit(f"ROM staging check failed: {record['slug']}")
            if (not card_file.is_file() or digest(card_file) != record["cardSha256"]
                    or digest(card_file) != digest(PREVIEWS / f"{record['slug']}.png")):
                raise SystemExit(f"Card staging check failed: {record['slug']}")
        print(f"Check passed: {len(records)} catalog records, ROMs, and card hashes")


if __name__ == "__main__":
    main()
