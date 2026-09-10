"""Pure crop / margin geometry.

All functions are deterministic and free of I/O. They consume
:class:`~bindery.models.crop.MarginSpec` and plain integer sizes so adapters
can map them onto Pillow without domain depending on Pillow.
"""

from __future__ import annotations

from bindery.domain.validate import ensure_positive_size
from bindery.exceptions import BinderyValidationError
from bindery.models.crop import CropBox, MarginSpec

__all__ = [
    "compute_output_size",
    "expand_box_by_margins",
    "is_valid_crop",
    "normalize_margins",
    "pad_image_size",
]


def compute_output_size(
    image_size: tuple[int, int],
    margins: MarginSpec,
) -> tuple[int, int]:
    """Return the padded canvas size for an image plus margins.

    Args:
        image_size: Source ``(width, height)`` in pixels. Both must be > 0.
        margins: Non-negative padding on each edge.

    Returns:
        tuple: ``(width + left + right, height + top + bottom)``.

    Raises:
        BinderyValidationError: If ``image_size`` has a non-positive dimension.

    Examples:
        >>> from bindery.models.crop import MarginSpec
        >>> compute_output_size((100, 50), MarginSpec(left=2, top=3, right=4, bottom=5))
        (106, 58)
    """
    width, height = ensure_positive_size(image_size, context="image")
    return (width + margins.horizontal, height + margins.vertical)


def pad_image_size(image_size: tuple[int, int], margins: MarginSpec) -> tuple[int, int]:
    """Alias of :func:`compute_output_size` for call-site clarity.

    Args:
        image_size: Source ``(width, height)`` in pixels.
        margins: Padding spec.

    Returns:
        tuple: Padded ``(width, height)``.

    Examples:
        >>> from bindery.models.crop import MarginSpec
        >>> pad_image_size((10, 20), MarginSpec(left=1, top=2, right=3, bottom=4))
        (14, 26)
    """
    return compute_output_size(image_size, margins)


def normalize_margins(
    margins: MarginSpec,
    image_size: tuple[int, int],
) -> MarginSpec:
    """Clamp margins so the padded canvas never collapses to zero area.

    Horizontal pads are scaled so ``left + right < width``. Vertical pads are
    scaled so ``top + bottom < height``. Individual edges stay non-negative and
    relative proportions are preserved when possible.

    Args:
        margins: Requested padding.
        image_size: Source ``(width, height)``. Both must be > 0.

    Returns:
        MarginSpec: Safe margins for this image size.

    Raises:
        BinderyValidationError: If ``image_size`` has a non-positive dimension.

    Examples:
        >>> from bindery.models.crop import MarginSpec
        >>> normalize_margins(MarginSpec.uniform(50), (20, 20)).left
        9
    """
    width, height = ensure_positive_size(image_size, context="image")

    def _fit(left: int, right: int, limit: int) -> tuple[int, int]:
        total = left + right
        if total < limit:
            return (left, right)
        if total == 0:
            return (0, 0)
        # Leave at least one pixel of content on this axis.
        max_total = limit - 1
        scale = max_total / total
        scaled_left = int(left * scale)
        scaled_right = max_total - scaled_left
        return (max(0, scaled_left), max(0, scaled_right))

    left, right = _fit(margins.left, margins.right, width)
    top, bottom = _fit(margins.top, margins.bottom, height)
    return MarginSpec(left=left, top=top, right=right, bottom=bottom)


def is_valid_crop(box: CropBox, image_size: tuple[int, int]) -> bool:
    """Return whether ``box`` lies entirely inside ``image_size``.

    Args:
        box: Crop rectangle (already validated for positive extent).
        image_size: Source ``(width, height)`` in pixels.

    Returns:
        bool: ``True`` if the box does not overflow the canvas.

    Examples:
        >>> from bindery.models.crop import CropBox
        >>> is_valid_crop(CropBox(0, 0, 10, 10), (10, 10))
        True
        >>> is_valid_crop(CropBox(0, 0, 11, 10), (10, 10))
        False
    """
    try:
        ensure_positive_size(image_size, context="image")
    except BinderyValidationError:
        return False
    return box.fits_in(image_size)


def expand_box_by_margins(box: CropBox, margins: MarginSpec) -> CropBox:
    """Grow ``box`` outward by ``margins``, clamping origin edges at zero.

    Args:
        box: Base crop rectangle.
        margins: Outward expansion amounts per edge.

    Returns:
        CropBox: Expanded rectangle. ``left``/``top`` never go below 0.

    Examples:
        >>> from bindery.models.crop import CropBox, MarginSpec
        >>> expand_box_by_margins(
        ...     CropBox(10, 10, 20, 20), MarginSpec.uniform(5)
        ... )
        CropBox(left=5, top=5, right=25, bottom=25)
    """
    left = max(0, box.left - margins.left)
    top = max(0, box.top - margins.top)
    right = box.right + margins.right
    bottom = box.bottom + margins.bottom
    # After clamping, extent remains positive because box.right > box.left >= 0
    # and right only grows; if left clamp pulled left up to 0 and box.left was
    # already 0, width only grows.
    if right <= left:
        right = left + box.width
    if bottom <= top:
        bottom = top + box.height
    return CropBox(left=left, top=top, right=right, bottom=bottom)
