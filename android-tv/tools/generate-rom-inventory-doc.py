#!/usr/bin/env python3
"""Copy published ROM card screenshots into docs and generate the inventory table."""
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "android-tv/app/build/generated/publishedLibrary"
CATALOG = BUILD / "library.json"
CARD_SOURCE = BUILD / "cards"
CARD_DEST = ROOT / "docs/plans/assets/snes-rom-library-cards"
DOC = ROOT / "docs/plans/2026-10-26-snes-rom-library-rom-inventory.md"


def cell(value):
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def main():
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    records = data["roms"]
    CARD_DEST.mkdir(parents=True, exist_ok=True)
    rows = []
    total_bytes = 0
    for record in records:
        slug = record["slug"]
        source = CARD_SOURCE / f"{slug}.png"
        target = CARD_DEST / f"{slug}.png"
        if not source.is_file():
            raise SystemExit(f"Missing screenshot card for {slug}: {source}")
        shutil.copyfile(source, target)
        total_bytes += int(record["size"])
        image = f'<img src="assets/snes-rom-library-cards/{slug}.png" width="96" height="84" alt="{cell(record["title"])} screenshot">'
        rows.append((record, image))

    lines = [
        "# Published SNES ROM library: complete inventory",
        "",
        f"**{len(records)} ROMs · {total_bytes:,} bytes ({total_bytes / (1024 * 1024):.1f} MiB)**",
        "",
        "Each row includes a small inline screenshot used by the TV library card. Cards are deterministic frame captures (frame number shown below); nearly blank frames use generated title-card artwork. These are the catalog's presentation images, not screenshots of the emulator UI.",
        "",
        "| # | Screenshot | ROM | Slug | Category | Size | Card frame |",
        "|---:|:---:|---|---|---|---:|---:|",
    ]
    for record, image in rows:
        lines.append("| " + " | ".join((
            str(record["order"]), image, cell(record["title"]), f'`{cell(record["slug"])}`',
            cell(record.get("categoryLabel", record.get("category"))),
            f'{int(record["size"]):,} B', str(record.get("cardFrame", "—")),
        )) + " |")
    lines.extend(("", "Source: the published catalog and ROM assets from `biohack.net` and `llvm-mos-65816`. The comparison benchmark uses only `mandel-display`; this full list documents the offline library packaged by the separate library flavor.", ""))
    DOC.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {DOC} with {len(records)} rows and inline screenshots.")


if __name__ == "__main__":
    main()
