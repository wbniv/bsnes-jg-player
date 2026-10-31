"""Shared SNES controller extraction and aspect-preserving placement helpers."""

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
CONTROLLER_BADGE = ROOT / "docs/plans/assets/snes-controller-badge.png"


def controller_badge() -> Image.Image:
    """Load the shared transparent North American SNES controller artwork."""
    return Image.open(CONTROLLER_BADGE).convert("RGBA")


def fit_controller(badge: Image.Image, max_size: tuple[int, int]) -> Image.Image:
    """Scale the badge to fit a bounding box without ever changing its aspect ratio."""
    fitted = badge.copy()
    fitted.thumbnail(max_size, Image.Resampling.LANCZOS)
    return fitted


def place_controller_bottom_right(
    canvas: Image.Image,
    badge: Image.Image,
    max_width_fraction: float = 0.40,
    max_height_fraction: float = 0.23,
    margin_fraction: float = 0.08,
) -> None:
    width, height = canvas.size
    fitted = fit_controller(
        badge,
        (round(width * max_width_fraction), round(height * max_height_fraction)),
    )
    margin = round(min(width, height) * margin_fraction)
    canvas.alpha_composite(fitted, (width - margin - fitted.width, height - margin - fitted.height))
