"""Tests for pure crop geometry."""

from __future__ import annotations

import pytest

from bindery.domain.geometry import (
    compute_output_size,
    expand_box_by_margins,
    is_valid_crop,
    normalize_margins,
    pad_image_size,
)
from bindery.exceptions import BinderyValidationError
from bindery.models.crop import CropBox, MarginSpec


def test_compute_output_size_adds_margins() -> None:
    """Output canvas is image size plus left+right and top+bottom pads."""
    margins = MarginSpec(left=2, top=3, right=4, bottom=5)
    assert compute_output_size((100, 50), margins) == (106, 58)


def test_compute_output_size_zero_margins() -> None:
    """Zero margins preserve dimensions."""
    assert compute_output_size((80, 40), MarginSpec()) == (80, 40)


def test_compute_output_size_rejects_non_positive_image() -> None:
    """Image dimensions must be positive integers."""
    with pytest.raises(BinderyValidationError):
        compute_output_size((0, 10), MarginSpec())
    with pytest.raises(BinderyValidationError):
        compute_output_size((10, -1), MarginSpec())


def test_normalize_margins_clamps_oversized_pads() -> None:
    """Clamping never produces a zero-area output canvas."""
    margins = MarginSpec(left=50, top=50, right=50, bottom=50)
    normalized = normalize_margins(margins, (20, 20))
    assert normalized.left + normalized.right < 20
    assert normalized.top + normalized.bottom < 20
    assert normalized.left >= 0
    size = compute_output_size((20, 20), normalized)
    assert size[0] >= 1
    assert size[1] >= 1


def test_normalize_margins_keeps_valid_values() -> None:
    """Already-valid margins pass through unchanged."""
    margins = MarginSpec.uniform(5)
    assert normalize_margins(margins, (100, 100)) == margins


def test_normalize_margins_rejects_bad_image_size() -> None:
    """Non-positive image size is rejected before clamping."""
    with pytest.raises(BinderyValidationError):
        normalize_margins(MarginSpec(), (0, 10))


def test_is_valid_crop_true_when_inside() -> None:
    """Box fully inside the canvas is valid."""
    box = CropBox(left=0, top=0, right=10, bottom=10)
    assert is_valid_crop(box, (10, 10)) is True


def test_is_valid_crop_false_when_overflows() -> None:
    """Box overflowing either axis is invalid."""
    box = CropBox(left=0, top=0, right=11, bottom=10)
    assert is_valid_crop(box, (10, 10)) is False


def test_expand_box_by_margins() -> None:
    """Outward expand grows the box by the margin insets, clamped at origin."""
    box = CropBox(left=10, top=10, right=20, bottom=20)
    expanded = expand_box_by_margins(box, MarginSpec(left=5, top=5, right=5, bottom=5))
    assert expanded == CropBox(left=5, top=5, right=25, bottom=25)


def test_expand_box_clamps_to_origin() -> None:
    """Expansion never goes negative on the origin edges."""
    box = CropBox(left=2, top=2, right=10, bottom=10)
    expanded = expand_box_by_margins(box, MarginSpec(left=10, top=10, right=0, bottom=0))
    assert expanded.left == 0
    assert expanded.top == 0
    assert expanded.right == 10
    assert expanded.bottom == 10


def test_pad_image_size_matches_compute_output_size() -> None:
    """Pad helper and output-size helper stay in lockstep."""
    margins = MarginSpec(left=1, top=2, right=3, bottom=4)
    assert pad_image_size((10, 20), margins) == compute_output_size((10, 20), margins)
