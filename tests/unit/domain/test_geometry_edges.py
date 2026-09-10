"""Edge-case tests for geometry helpers."""

from __future__ import annotations

from bindery.domain.geometry import is_valid_crop, normalize_margins
from bindery.models.crop import CropBox, MarginSpec


def test_normalize_margins_asymmetric() -> None:
    """Asymmetric pads keep proportions when clamping."""
    margins = MarginSpec(left=30, top=0, right=10, bottom=0)
    result = normalize_margins(margins, (20, 20))
    assert result.horizontal < 20
    assert result.left > result.right


def test_is_valid_crop_false_on_bad_image_size() -> None:
    """Invalid canvas size yields False rather than raising."""
    box = CropBox(0, 0, 1, 1)
    assert is_valid_crop(box, (0, 10)) is False
    assert is_valid_crop(box, (10, -1)) is False


def test_normalize_margins_zero_on_zero_image_axes() -> None:
    """Degenerate zero pads stay zero."""
    result = normalize_margins(MarginSpec(left=0, right=0, top=0, bottom=0), (5, 5))
    assert result == MarginSpec()
