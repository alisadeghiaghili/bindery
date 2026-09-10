"""Tests for image load and transform adapters."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from bindery.adapters.images import (
    load_image,
    pad_to_canvas,
    stamp_page_number,
    to_grayscale,
)
from bindery.exceptions import BinderyIOError, BinderyValidationError
from bindery.models.crop import MarginSpec


def test_load_image_rgb(tmp_path: Path) -> None:
    """PNG loads as RGB."""
    path = tmp_path / "a.png"
    Image.new("L", (8, 8), 10).save(path)
    image = load_image(path)
    assert image.mode == "RGB"
    assert image.size == (8, 8)


def test_load_image_missing(tmp_path: Path) -> None:
    """Missing file raises BinderyIOError."""
    with pytest.raises(BinderyIOError, match="cannot read"):
        load_image(tmp_path / "missing.png")


def test_pad_adds_white_margins() -> None:
    """Padding grows the canvas and keeps the core image."""
    image = Image.new("RGB", (10, 10), (255, 0, 0))
    margins = MarginSpec(left=2, top=3, right=4, bottom=5)
    padded = pad_to_canvas(image, margins)
    assert padded.size == (16, 18)
    # Core pixel stays red
    assert padded.getpixel((5, 5)) == (255, 0, 0)
    # Corner is white margin
    assert padded.getpixel((0, 0)) == (255, 255, 255)


def test_pad_zero_margins_identity_size() -> None:
    """Zero margins preserve size."""
    image = Image.new("RGB", (7, 9), (0, 0, 0))
    padded = pad_to_canvas(image, MarginSpec())
    assert padded.size == (7, 9)


def test_to_grayscale_mode_l() -> None:
    """Grayscale conversion produces mode L."""
    image = Image.new("RGB", (4, 4), (10, 20, 30))
    gray = to_grayscale(image)
    assert gray.mode == "L"
    assert gray.size == (4, 4)


def test_stamp_page_number_draws_and_keeps_size() -> None:
    """Stamp writes a footer without resizing the canvas."""
    image = Image.new("RGB", (80, 40), (255, 255, 255))
    stamped = stamp_page_number(image, page_number=7)
    assert stamped.size == image.size
    # Bottom band should differ from pure white where the digit was drawn
    bottom = stamped.crop((0, 30, 80, 40))
    colors = bottom.getcolors(maxcolors=10_000) or []
    assert len(colors) > 1


def test_stamp_rejects_negative_page_number() -> None:
    """Page numbers for stamping are non-negative."""
    image = Image.new("RGB", (10, 10), (255, 255, 255))
    with pytest.raises(BinderyValidationError, match="page number"):
        stamp_page_number(image, page_number=-1)


def test_pipeline_transforms_compose() -> None:
    """Load → pad → gray → stamp stays RGB canvas with gray content."""
    image = Image.new("RGB", (20, 20), (200, 0, 0))
    padded = pad_to_canvas(image, MarginSpec.uniform(2))
    gray = to_grayscale(padded)
    # stamp expects RGB for colored text; convert back for compositing
    stamped = stamp_page_number(gray.convert("RGB"), page_number=1)
    assert stamped.size == (24, 24)
