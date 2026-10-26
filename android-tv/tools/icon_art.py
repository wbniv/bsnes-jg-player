"""Shared SNES controller extraction and aspect-preserving placement helpers."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


def controller_cutout(master_path: Path) -> Image.Image:
    source = Image.open(master_path).convert("RGBA")
    pad = source.crop((885, 1030, 1235, 1230))
    mask = Image.new("L", pad.size, 0)
    ImageDraw.Draw(mask).polygon(
        [
            (52, 87), (59, 67), (76, 52), (99, 45), (126, 48),
            (150, 53), (197, 53), (218, 47), (254, 47), (280, 54),
            (301, 68), (317, 89), (323, 111), (318, 132), (304, 150),
            (283, 160), (258, 162), (235, 156), (209, 143), (137, 143),
            (113, 155), (87, 161), (65, 155), (49, 141), (41, 123),
            (41, 103),
        ],
        fill=255,
    )
    mask = mask.filter(ImageFilter.GaussianBlur(0.7))
    pad.putalpha(mask)
    return pad.crop(mask.getbbox())


def fit_controller(badge: Image.Image, max_size: tuple[int, int]) -> Image.Image:
    """Scale the badge to fit a bounding box without ever changing its aspect ratio."""
    fitted = badge.copy()
    fitted.thumbnail(max_size, Image.Resampling.LANCZOS)
    return fitted


def place_controller_bottom_right(
    canvas: Image.Image,
    badge: Image.Image,
    max_width_fraction: float = 0.205,
    max_height_fraction: float = 0.18,
    margin_fraction: float = 0.025,
) -> None:
    width, height = canvas.size
    fitted = fit_controller(
        badge,
        (round(width * max_width_fraction), round(height * max_height_fraction)),
    )
    margin = round(min(width, height) * margin_fraction)
    canvas.alpha_composite(fitted, (width - margin - fitted.width, height - margin - fitted.height))
