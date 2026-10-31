#!/usr/bin/env python3
"""Build the Mandelbrot app icon from its reference frame and shared SNES badge."""

from pathlib import Path

from PIL import Image, ImageOps

from icon_art import controller_badge, place_controller_bottom_right

ROOT = Path(__file__).resolve().parents[2]
FRAME = ROOT / "android/fixture/reference-5800.png"
OUTPUT = ROOT / "docs/plans/assets/mandel-display-app-icon.png"
SIZE = 1254


def main() -> None:
    if not FRAME.is_file():
        raise SystemExit(f"missing frame-5800 reference: {FRAME}")
    artwork = ImageOps.fit(
        Image.open(FRAME).convert("RGB"), (SIZE, SIZE),
        method=Image.Resampling.NEAREST,
    ).convert("RGBA")
    place_controller_bottom_right(artwork, controller_badge())
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    artwork.convert("RGB").save(OUTPUT, optimize=True)
    print(f"Wrote {OUTPUT} from the frame-5800 reference and shared SNES badge.")


if __name__ == "__main__":
    main()
