#!/usr/bin/env python3
"""Render the two approved app icons at documented launcher and mobile pixel sizes."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from icon_art import controller_cutout, place_controller_bottom_right

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "docs/plans/assets"
OUT = ASSETS / "actual-size-renders"
PRODUCTS = {
    "mandelbrot": ASSETS / "mandel-display-app-icon.png",
    "suite": ASSETS / "snes-rom-suite-app-icon.png",
}
BANNER_ARTWORK = {
    "mandelbrot": ROOT / "android-tv/fixture/reference-5800.png",
    "suite": ASSETS / "snes-rom-suite-mosaic.png",
}
TV_ICONS = {"mdpi": 80, "hdpi": 120, "xhdpi": 160, "xxhdpi": 240, "xxxhdpi": 320}
TV_BANNERS = {
    "mdpi": (160, 90),
    "hdpi": (240, 135),
    "xhdpi": (320, 180),
    "xxhdpi": (480, 270),
    "xxxhdpi": (640, 360),
}
WEB_SIZES = (16, 32, 48, 180, 192, 512)


def save_size(source: Image.Image, path: Path, size: tuple[int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    source.resize(size, Image.Resampling.LANCZOS).save(path, optimize=True)


def make_banner(artwork: Image.Image, badge: Image.Image, subtitle: str) -> Image.Image:
    canvas = Image.new("RGB", (640, 360), "#0a0b27")
    draw = ImageDraw.Draw(canvas)
    draw.ellipse((-175, -180, 380, 375), fill="#17134b")
    tile = ImageOps.fit(artwork, (276, 276), method=Image.Resampling.LANCZOS)
    canvas.paste(tile, (36, 42))
    regular = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    bold = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    title_font = ImageFont.truetype(str(bold), 43) if bold.exists() else ImageFont.load_default()
    small_font = ImageFont.truetype(str(regular), 19) if regular.exists() else ImageFont.load_default()
    draw.text((348, 139), "bsnes-jg", font=title_font, fill="#f1eaff")
    draw.text((352, 198), subtitle, font=small_font, fill="#b9a8d7")
    draw.rounded_rectangle((352, 238, 473, 243), radius=2, fill="#8154d6")
    banner = canvas.convert("RGBA")
    place_controller_bottom_right(banner, badge)
    return banner.convert("RGB")


def main() -> None:
    for name, master_path in PRODUCTS.items():
        if not master_path.is_file():
            raise SystemExit(f"missing icon master: {master_path}")
        master = Image.open(master_path).convert("RGB")
        art_path = BANNER_ARTWORK[name]
        if not art_path.is_file():
            raise SystemExit(f"missing banner artwork: {art_path}; regenerate the suite mosaic first")
        artwork = Image.open(art_path).convert("RGB")
        badge = controller_cutout(PRODUCTS["mandelbrot"])
        for density, size in TV_ICONS.items():
            save_size(master, OUT / name / "tv" / f"launcher-{density}-{size}.png", (size, size))
        subtitle = "MANDELBROT PLAYER" if name == "mandelbrot" else "152 ROM SUITE"
        banner = make_banner(artwork, badge, subtitle)
        for density, size in TV_BANNERS.items():
            save_size(banner, OUT / name / "tv" / f"banner-{density}-{size[0]}x{size[1]}.png", size)
        for size in WEB_SIZES:
            save_size(master, OUT / name / "web-mobile" / f"icon-{size}.png", (size, size))
    print(f"Wrote TV launcher, TV banner, and web/mobile renders for both app identities under {OUT}.")


if __name__ == "__main__":
    main()
