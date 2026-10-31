#!/usr/bin/env python3
"""Compose a full-suite icon from real ROM preview frames and the approved controller badge."""

from pathlib import Path

from PIL import Image, ImageDraw

from icon_art import controller_badge, place_controller_bottom_right

ROOT = Path(__file__).resolve().parents[2]
PREVIEWS = ROOT.parent / "biohack.net/public/play/preview"
OUTPUT = ROOT / "docs/plans/assets/snes-rom-suite-app-icon.png"
MOSAIC = ROOT / "docs/plans/assets/snes-rom-suite-mosaic.png"

# A cross-section of the shipped SNES library: cellular art, games, raycasting,
# motion and signals. N-body adds orbit geometry at bottom-left; the Median
# Denoiser's broad blue field sits bottom-right, with its black right side behind the badge.
ROM_FRAMES = [
    "doom-fire",
    "space-invaders",
    "raycaster",
    "lzss-gallery",
    "boids",
    "cardioid",
    "n-body",
    "life",
    "medfilt",
]


def square_frame(path: Path, size: int) -> Image.Image:
    frame = Image.open(path).convert("RGB")
    width, height = frame.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    return frame.crop((left, top, left + side, top + side)).resize(
        (size, size), Image.Resampling.NEAREST
    )


def main() -> None:
    frames = [PREVIEWS / f"{slug}.png" for slug in ROM_FRAMES]
    missing = [str(path) for path in frames if not path.is_file()]
    if missing:
        raise SystemExit("Missing ROM preview(s):\n" + "\n".join(missing))

    size, gutter, outer = 166, 5, 2
    canvas = Image.new("RGB", (512, 512), "#09091b")
    for index, frame_path in enumerate(frames):
        col, row = index % 3, index // 3
        x = outer + col * (size + gutter)
        y = outer + row * (size + gutter)
        canvas.paste(square_frame(frame_path, size), (x, y))

    # A restrained violet grid edge unifies screenshots from very different ROMs.
    draw = ImageDraw.Draw(canvas)
    for offset in (169, 340):
        draw.rectangle((offset, 0, offset + 2, 511), fill="#342563")
        draw.rectangle((0, offset, 511, offset + 2), fill="#342563")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(MOSAIC, optimize=True)
    canvas = canvas.convert("RGBA")
    place_controller_bottom_right(canvas, controller_badge())
    canvas.convert("RGB").save(OUTPUT, optimize=True)
    print(f"Wrote {OUTPUT} from {len(frames)} published ROM preview frames.")


if __name__ == "__main__":
    main()
