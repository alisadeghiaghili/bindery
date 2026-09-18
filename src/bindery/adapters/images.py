"""Pillow-backed image transforms."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from bindery.exceptions import BinderyIOError, BinderyValidationError
from bindery.models.crop import CropBox, MarginSpec

__all__ = [
    "crop_image",
    "fit_image_to_page",
    "load_image",
    "pad_to_canvas",
    "rotate_image",
    "save_page_image",
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
        >>> import tempfile
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


def crop_image(image: Image.Image, box: CropBox) -> Image.Image:
    """Crop ``image`` to ``box`` (exclusive right/bottom).

    Args:
        image: Source image.
        box: Crop rectangle in source pixels.

    Returns:
        PIL.Image.Image: New cropped image; input is not mutated.

    Raises:
        BinderyValidationError: If the box does not fit the image.

    Examples:
        >>> from PIL import Image
        >>> from bindery.models.crop import CropBox
        >>> crop_image(Image.new("RGB", (10, 10)), CropBox(0, 0, 4, 5)).size
        (4, 5)
    """
    width, height = image.size
    if not box.fits_in((width, height)):
        raise BinderyValidationError(f"crop {box} does not fit image size {(width, height)}")
    return image.crop(box.as_pil_box())


def rotate_image(image: Image.Image, degrees: int) -> Image.Image:
    """Rotate image clockwise by ``degrees``.

    Args:
        image: Source image.
        degrees: Clockwise angle; must be 0, 90, 180, or 270.

    Returns:
        PIL.Image.Image: New rotated image; input is not mutated.

    Raises:
        BinderyValidationError: If degrees is not a supported right angle.

    Examples:
        >>> from PIL import Image
        >>> rotate_image(Image.new("RGB", (10, 4)), 90).size
        (4, 10)
    """
    if degrees % 90 != 0 or degrees % 360 not in (0, 90, 180, 270):
        raise BinderyValidationError(f"rotate must be 0/90/180/270, got {degrees!r}")
    if degrees % 360 == 0:
        return image.copy()
    return image.rotate(-degrees, expand=True)


def pad_to_canvas(image: Image.Image, margins: MarginSpec) -> Image.Image:
    """Expand ``image`` with white margins.

    Args:
        image: Source image (any mode). Alpha is dropped by prior RGB convert
            in :func:`load_image`.
        margins: Non-negative pixel padding per edge. Fill is white.

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


def fit_image_to_page(
    image: Image.Image,
    page_size_pt: tuple[float, float],
    dpi: int,
) -> Image.Image:
    """Letterbox ``image`` onto a white canvas sized for a fixed PDF page.

    Args:
        image: Transformed page image.
        page_size_pt: Target page box in PDF points ``(width, height)``.
        dpi: Pixels per inch used to convert points to canvas pixels.

    Returns:
        PIL.Image.Image: RGB canvas with the image centered and scaled to fit.

    Raises:
        BinderyValidationError: If dpi is not a positive int.

    Examples:
        >>> from PIL import Image
        >>> fit_image_to_page(Image.new("RGB", (20, 20)), (72.0, 72.0), 72).size
        (72, 72)
    """
    if not isinstance(dpi, int) or isinstance(dpi, bool) or dpi <= 0:
        raise BinderyValidationError(f"dpi must be a positive int, got {dpi!r}")
    width_pt, height_pt = page_size_pt
    canvas_w = max(1, round(width_pt * dpi / 72.0))
    canvas_h = max(1, round(height_pt * dpi / 72.0))
    canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
    src = image if image.mode == "RGB" else image.convert("RGB")
    scale = min(canvas_w / src.width, canvas_h / src.height)
    new_w = max(1, int(src.width * scale))
    new_h = max(1, int(src.height * scale))
    resized = src.resize((new_w, new_h), Image.Resampling.LANCZOS)
    x = (canvas_w - new_w) // 2
    y = (canvas_h - new_h) // 2
    canvas.paste(resized, (x, y))
    return canvas


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


def save_page_image(
    image: Image.Image,
    path: Path,
    *,
    compress: str = "lossless",
    jpeg_quality: int = 85,
) -> Path:
    """Write a transformed page for PDF embed or preview.

    Args:
        image: Page image to write.
        path: Destination path (suffix may be rewritten for jpeg).
        compress: ``lossless`` writes PNG; ``jpeg`` writes JPEG.
        jpeg_quality: Quality 1-95 used when ``compress='jpeg'``.

    Returns:
        Path: Path actually written.

    Raises:
        BinderyValidationError: On invalid compress/quality.
        BinderyIOError: If the write fails.

    Examples:
        >>> from pathlib import Path
        >>> from PIL import Image
        >>> import tempfile
        >>> p = Path(tempfile.mkdtemp()) / "p.png"
        >>> save_page_image(Image.new("RGB", (4, 4)), p).name
        'p.png'
    """
    mode = str(compress).strip().lower()
    if mode not in {"lossless", "jpeg"}:
        raise BinderyValidationError(f"compress must be lossless or jpeg, got {compress!r}")
    if not isinstance(jpeg_quality, int) or isinstance(jpeg_quality, bool):
        raise BinderyValidationError(f"jpeg_quality must be an int, got {type(jpeg_quality)!r}")
    if jpeg_quality < 1 or jpeg_quality > 95:
        raise BinderyValidationError(f"jpeg_quality must be in 1..95, got {jpeg_quality}")

    target = Path(path)
    if mode == "jpeg":
        target = target.with_suffix(".jpg")
        save_image = image if image.mode == "RGB" else image.convert("RGB")
        fmt = "JPEG"
        options = {"quality": jpeg_quality, "optimize": True}
    else:
        target = target.with_suffix(".png")
        save_image = image
        fmt = "PNG"
        options = {"optimize": True}

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        save_image.save(target, format=fmt, **options)
    except OSError as exc:
        raise BinderyIOError(f"cannot write page image: {target}: {exc}") from exc
    return target
