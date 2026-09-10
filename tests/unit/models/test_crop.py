"""Tests for margin and crop-box models."""

from __future__ import annotations

import pytest

from bindery.exceptions import BinderyValidationError
from bindery.models.crop import CropBox, MarginSpec


def test_default_margins_are_zero() -> None:
    """New margin specs start with every edge at zero."""
    margins = MarginSpec()
    assert margins.left == 0
    assert margins.top == 0
    assert margins.right == 0
    assert margins.bottom == 0


def test_uniform_margins() -> None:
    """``uniform`` sets all four edges to the same non-negative value."""
    margins = MarginSpec.uniform(12)
    assert (margins.left, margins.top, margins.right, margins.bottom) == (12, 12, 12, 12)


def test_uniform_rejects_negative() -> None:
    """Negative padding is a validation error, not silent clamp."""
    with pytest.raises(BinderyValidationError, match="non-negative"):
        MarginSpec.uniform(-1)


def test_margins_are_frozen() -> None:
    """Margin specs are immutable value objects."""
    margins = MarginSpec()
    with pytest.raises((AttributeError, TypeError)):
        margins.left = 5  # type: ignore[misc]


def test_margin_as_inset_tuple() -> None:
    """``as_inset`` returns Pillow-compatible (left, top, right, bottom)."""
    margins = MarginSpec(left=1, top=2, right=3, bottom=4)
    assert margins.as_inset() == (1, 2, 3, 4)


def test_crop_box_dimensions() -> None:
    """Width/height are exclusive-edge derived sizes."""
    box = CropBox(left=10, top=20, right=110, bottom=220)
    assert box.width == 100
    assert box.height == 200


def test_crop_box_rejects_non_positive_extent() -> None:
    """Zero or inverted boxes cannot exist."""
    with pytest.raises(BinderyValidationError):
        CropBox(left=10, top=10, right=10, bottom=20)
    with pytest.raises(BinderyValidationError):
        CropBox(left=10, top=10, right=5, bottom=20)


def test_crop_box_rejects_negative_origin() -> None:
    """Origin cannot be negative."""
    with pytest.raises(BinderyValidationError):
        CropBox(left=-1, top=0, right=10, bottom=10)


def test_crop_box_area() -> None:
    """Area is width times height."""
    box = CropBox(left=0, top=0, right=3, bottom=4)
    assert box.area == 12


def test_crop_box_within_image() -> None:
    """``fits_in`` is true only when the box is fully inside the canvas."""
    box = CropBox(left=0, top=0, right=10, bottom=10)
    assert box.fits_in((10, 10))
    assert box.fits_in((20, 20))
    assert not box.fits_in((9, 20))
    assert not box.fits_in((20, 9))
