"""Shared image fixtures for adapter tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image


@pytest.fixture
def rgb_pages(tmp_path: Path) -> Path:
    """Create three small RGB PNG pages with distinct solid colors."""
    source = tmp_path / "pages"
    source.mkdir()
    colors = [(200, 30, 30), (30, 200, 30), (30, 30, 200)]
    for index, color in enumerate(colors):
        image = Image.new("RGB", (40, 60), color)
        image.save(source / f"page_{index + 1}.png")
    return source


@pytest.fixture
def mixed_name_pages(tmp_path: Path) -> Path:
    """Create pages whose names require natural sort (1, 2, 10)."""
    source = tmp_path / "mixed"
    source.mkdir()
    for name in ("page_10.png", "page_2.png", "page_1.png"):
        Image.new("RGB", (10, 10), (128, 128, 128)).save(source / name)
    return source
