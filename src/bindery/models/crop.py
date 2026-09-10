"""Crop and margin value objects.

Pure data: no I/O, no Pillow types. Geometry helpers in
:mod:`bindery.domain.geometry` consume these objects.
"""

from __future__ import annotations

from dataclasses import dataclass

from bindery.exceptions import BinderyValidationError

__all__ = ["CropBox", "MarginSpec"]


def _require_non_negative_int(value: object, name: str) -> int:
    """Validate that ``value`` is a non-negative ``int``.

    Args:
        value: Candidate field value.
        name: Field name used in error messages.

    Returns:
        int: The validated value.

    Raises:
        BinderyValidationError: If the value is not a non-negative int.
    """
    if not isinstance(value, int) or isinstance(value, bool):
        raise BinderyValidationError(f"{name} must be an int, got {type(value)!r}")
    if value < 0:
        raise BinderyValidationError(f"{name} must be non-negative, got {value}")
    return value


def _require_int(value: object, name: str) -> int:
    """Validate that ``value`` is an ``int`` (sign unchecked).

    Args:
        value: Candidate field value.
        name: Field name used in error messages.

    Returns:
        int: The validated value.

    Raises:
        BinderyValidationError: If the value is not an int.
    """
    if not isinstance(value, int) or isinstance(value, bool):
        raise BinderyValidationError(f"{name} must be an int, got {type(value)!r}")
    return value


@dataclass(frozen=True, slots=True)
class MarginSpec:
    """Padding applied around an image when building the output canvas.

    All values are non-negative pixel counts.

    Attributes:
        left: Pixels of padding on the left edge.
        top: Pixels of padding on the top edge.
        right: Pixels of padding on the right edge.
        bottom: Pixels of padding on the bottom edge.

    Examples:
        >>> margins = MarginSpec.uniform(10)
        >>> margins.as_inset()
        (10, 10, 10, 10)
    """

    left: int = 0
    top: int = 0
    right: int = 0
    bottom: int = 0

    def __post_init__(self) -> None:
        """Reject negative edge values at construction time.

        Raises:
            BinderyValidationError: If any edge is negative or not an int.
        """
        for name in ("left", "top", "right", "bottom"):
            _require_non_negative_int(getattr(self, name), f"margin {name}")

    @classmethod
    def uniform(cls, value: int) -> MarginSpec:
        """Build equal padding on all four edges.

        Args:
            value: Pixel count applied to every edge. Must be >= 0.

        Returns:
            MarginSpec: Spec with all edges set to ``value``.

        Raises:
            BinderyValidationError: If ``value`` is negative or not an int.

        Examples:
            >>> MarginSpec.uniform(4).bottom
            4
        """
        checked = _require_non_negative_int(value, "margin value")
        return cls(left=checked, top=checked, right=checked, bottom=checked)

    def as_inset(self) -> tuple[int, int, int, int]:
        """Return Pillow ``ImageOps.expand``-style insets.

        Returns:
            tuple: ``(left, top, right, bottom)`` in pixels.
        """
        return (self.left, self.top, self.right, self.bottom)

    @property
    def horizontal(self) -> int:
        """Total horizontal padding.

        Returns:
            int: ``left + right``.
        """
        return self.left + self.right

    @property
    def vertical(self) -> int:
        """Total vertical padding.

        Returns:
            int: ``top + bottom``.
        """
        return self.top + self.bottom


@dataclass(frozen=True, slots=True)
class CropBox:
    """Axis-aligned crop rectangle with exclusive right/bottom edges.

    Matches PIL ``box`` semantics: ``left <= x < right``, ``top <= y < bottom``.

    Attributes:
        left: Left edge (inclusive), pixels, >= 0.
        top: Top edge (inclusive), pixels, >= 0.
        right: Right edge (exclusive), must be > left.
        bottom: Bottom edge (exclusive), must be > top.

    Examples:
        >>> box = CropBox(left=0, top=0, right=4, bottom=6)
        >>> box.width, box.height, box.area
        (4, 6, 24)
    """

    left: int
    top: int
    right: int
    bottom: int

    def __post_init__(self) -> None:
        """Validate non-negative origin and positive extent.

        Raises:
            BinderyValidationError: If origin is negative, edges are not ints,
                or extent is not positive.
        """
        _require_non_negative_int(self.left, "crop left")
        _require_non_negative_int(self.top, "crop top")
        _require_int(self.right, "crop right")
        _require_int(self.bottom, "crop bottom")
        if self.right <= self.left:
            raise BinderyValidationError(
                f"crop right ({self.right}) must be greater than left ({self.left})"
            )
        if self.bottom <= self.top:
            raise BinderyValidationError(
                f"crop bottom ({self.bottom}) must be greater than top ({self.top})"
            )

    @property
    def width(self) -> int:
        """Crop width in pixels.

        Returns:
            int: ``right - left``.
        """
        return self.right - self.left

    @property
    def height(self) -> int:
        """Crop height in pixels.

        Returns:
            int: ``bottom - top``.
        """
        return self.bottom - self.top

    @property
    def area(self) -> int:
        """Crop area in square pixels.

        Returns:
            int: ``width * height``.
        """
        return self.width * self.height

    def fits_in(self, image_size: tuple[int, int]) -> bool:
        """Return whether this box lies entirely inside ``image_size``.

        Args:
            image_size: ``(width, height)`` of the source image in pixels.

        Returns:
            bool: ``True`` if the box does not overflow either axis.

        Examples:
            >>> CropBox(0, 0, 5, 5).fits_in((5, 5))
            True
            >>> CropBox(0, 0, 6, 5).fits_in((5, 5))
            False
        """
        width, height = image_size
        return self.right <= width and self.bottom <= height

    def as_pil_box(self) -> tuple[int, int, int, int]:
        """Return a tuple suitable for ``PIL.Image.crop``.

        Returns:
            tuple: ``(left, top, right, bottom)``.
        """
        return (self.left, self.top, self.right, self.bottom)
