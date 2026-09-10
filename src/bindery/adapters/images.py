"""Pillow-backed image transforms."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from bindery.exceptions import BinderyIOError, BinderyValidationError
from bindery.models.crop import MarginSpec

__all__ = [
    "load_image",
    "pad_to_canvas",
    "stamp_page_number",
    "to_grayscale",
]


def load_image(path: Path) -> Image.Image:
    """Load an image file as an in-memory RGB image.

    Args:
        path: Path to an existing image file.

    Returns:
        PIL.Image.Image: Decoded RGB image. Callers own the instance and should
        close it when finished.

    Raises:
        BinderyIOError: If the file is missing or cannot be decoded.

    Examples:
        >>> from pathlib import Path
        >>> from PIL import Image
        >>> import tempfile, os
        >>> d = tempfile.mkdtemp()
        >>> p = Path(d) / "a.png"
        >>> Image.new("RGB", (2, 2), (1, 2, 3)).save(p)
        >>> load_image(p).size
        (2, 2)
    """
    image_path = Path(path)
    try:
        with Image.open(image_path) as raw:
            image = raw.convert("RGB")
            image.load()
    except FileNotFoundError as exc:
        raise BinderyIOError(f"cannot read image: {image_path}") from exc
    except OSError as exc:
        raise BinderyIOError(f"cannot decode image: {image_path}: {exc}") from exc
    return image


def pad_to_canvas(image: Image.Image, margins: MarginSpec) -> Image.Image:
    """Expand ``image`` with white (or black for L) margins.

    Args:
        image: Source image (any mode; alpha is dropped by prior RGB convert).
        margins: Non-negative pixel padding per edge.

    Returns:
        PIL.Image.Image: New padded image; input is not mutated.

    Examples:
        >>> from PIL import Image
        >>> from bindery.models.crop import MarginSpec
        >>> pad_to_canvas(Image.new("RGB", (10, 10)), MarginSpec.uniform(1)).size
        (12, 12)
    """
    return ImageOps.expand(image, border=margins.as_inset(), fill=(255, 255, 255))


def to_grayscale(image: Image.Image) -> Image.Image:
    """Convert an image to 8-bit grayscale (mode ``L``).

    Args:
        image: Source image.

    Returns:
        PIL.Image.Image: New grayscale image; input is not mutated.

    Examples:
        >>> from PIL import Image
        >>> to_grayscale(Image.new("RGB", (3, 3))).mode
        'L'
    """
    return image.convert("L")


def stamp_page_number(image: Image.Image, page_number: int) -> Image.Image:
    """Draw a centered page number in the bottom margin band.

    Args:
        image: Canvas image (RGB recommended). Copied before drawing.
        page_number: Human-facing page number to stamp. Must be >= 0.

    Returns:
        PIL.Image.Image: New image with the stamp drawn.

    Raises:
        BinderyValidationError: If ``page_number`` is negative.

    Examples:
        >>> from PIL import Image
        >>> stamp_page_number(Image.new("RGB", (40, 20), (255, 255, 255)), 3).size
        (40, 20)
    """
    if not isinstance(page_number, int) or isinstance(page_number, bool):
        raise BinderyValidationError(f"page number must be an int, got {type(page_number)!r}")
    if page_number < 0:
        raise BinderyValidationError(f"page number must be >= 0, got {page_number}")

    canvas = image.copy()
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    text = str(page_number)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    text_width = right - left
    text_height = bottom - top
    width, height = canvas.size
    x = (width - text_width) // 2
    y = max(0, height - text_height - 2)
    draw.text((x, y), text, fill=(0, 0, 0), font=font)
    return canvas
