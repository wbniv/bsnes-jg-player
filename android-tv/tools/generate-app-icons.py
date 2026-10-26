#!/usr/bin/env python3
"""Generate Android TV launcher/banner and browser/mobile icons from the suite artwork."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from icon_art import controller_cutout, place_controller_bottom_right

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "docs/plans/assets/snes-rom-suite-app-icon.png"
MOSAIC = ROOT / "docs/plans/assets/snes-rom-suite-mosaic.png"
CONTROLLER_SOURCE = ROOT / "docs/plans/assets/mandel-display-app-icon.png"
ANDROID_RES = ROOT / "android-tv/app/src/main/res"
WEB_ICONS = ROOT / "web/icons"

TV_LAUNCHER = {
    "mdpi": 80,
    "hdpi": 120,
    "xhdpi": 160,
    "xxhdpi": 240,
    "xxxhdpi": 320,
}
TV_BANNER = {
    "mdpi": (160, 90),
    "hdpi": (240, 135),
    "xhdpi": (320, 180),
    "xxhdpi": (480, 270),
    "xxxhdpi": (640, 360),
}


def save_resize(source: Image.Image, path: Path, size: tuple[int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    source.resize(size, Image.Resampling.LANCZOS).save(path, optimize=True)


def make_banner() -> Image.Image:
    canvas = Image.new("RGB", (640, 360), "#0a0b27")
    draw = ImageDraw.Draw(canvas)
    # Soft, restrained color field echoes the ROM image while leaving a quiet title area.
    draw.rectangle((0, 0, 639, 359), fill="#0a0b27")
    draw.ellipse((-175, -180, 380, 375), fill="#17134b")
    artwork = Image.open(MOSAIC).convert("RGB")
    tile = ImageOps.fit(artwork, (276, 276), method=Image.Resampling.LANCZOS)
    canvas.paste(tile, (36, 42))

    regular = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    bold = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    title_font = ImageFont.truetype(str(bold), 43) if bold.exists() else ImageFont.load_default()
    subtitle_font = ImageFont.truetype(str(regular), 19) if regular.exists() else ImageFont.load_default()
    draw.text((348, 139), "bsnes-jg", font=title_font, fill="#f1eaff", stroke_width=0)
    draw.text((352, 198), "LLVM 65816 ROM SUITE", font=subtitle_font, fill="#b9a8d7")
    draw.rounded_rectangle((352, 238, 473, 243), radius=2, fill="#8154d6")
    banner = canvas.convert("RGBA")
    place_controller_bottom_right(banner, controller_cutout(CONTROLLER_SOURCE))
    return banner.convert("RGB")


def main() -> None:
    for source in (MASTER, MOSAIC, CONTROLLER_SOURCE):
        if not source.is_file():
            raise SystemExit(f"missing suite icon source: {source}")
    icon = Image.open(MASTER).convert("RGB")

    for density, size in TV_LAUNCHER.items():
        save_resize(icon, ANDROID_RES / f"mipmap-{density}/ic_launcher.png", (size, size))

    banner = make_banner()
    for density, size in TV_BANNER.items():
        save_resize(banner, ANDROID_RES / f"mipmap-{density}/tv_banner.png", size)

    WEB_ICONS.mkdir(parents=True, exist_ok=True)
    for size in (16, 32, 48, 180, 192, 512):
        save_resize(icon, WEB_ICONS / f"icon-{size}.png", (size, size))
    icon.resize((512, 512), Image.Resampling.LANCZOS).save(
        WEB_ICONS / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48)]
    )

    print("Generated Android TV launcher icons (80–320 px), TV banners (160x90–640x360),")
    print("and web/mobile icons (16–512 px) from the updated full-suite artwork.")


if __name__ == "__main__":
    main()
