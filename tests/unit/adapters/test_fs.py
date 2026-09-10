"""Tests for filesystem discovery of page images."""

from __future__ import annotations

from pathlib import Path

import pytest

from bindery.adapters.fs import discover_page_files, list_image_paths
from bindery.exceptions import BinderyIOError, BinderyValidationError


def test_list_image_paths_natural_order(mixed_name_pages: Path) -> None:
    """Images sort naturally: page_1, page_2, page_10."""
    paths = list_image_paths(mixed_name_pages)
    assert [p.name for p in paths] == ["page_1.png", "page_2.png", "page_10.png"]


def test_list_image_paths_skips_non_images(tmp_path: Path) -> None:
    """Non-image files are ignored."""
    source = tmp_path / "pages"
    source.mkdir()
    (source / "notes.txt").write_text("ignore", encoding="utf-8")
    (source / "page_1.png").write_bytes(b"")
    # empty png is not openable later, but discovery still returns it by suffix
    paths = list_image_paths(source)
    assert [p.name for p in paths] == ["page_1.png"]


def test_list_image_paths_missing_dir(tmp_path: Path) -> None:
    """Missing source directory raises a clear I/O error."""
    with pytest.raises(BinderyIOError, match="does not exist"):
        list_image_paths(tmp_path / "nope")


def test_list_image_paths_not_a_directory(tmp_path: Path) -> None:
    """A file path is rejected."""
    target = tmp_path / "file.txt"
    target.write_text("x", encoding="utf-8")
    with pytest.raises(BinderyIOError, match="not a directory"):
        list_image_paths(target)


def test_discover_page_files_empty_dir(tmp_path: Path) -> None:
    """Empty source is a validation error, not a silent empty PDF."""
    source = tmp_path / "empty"
    source.mkdir()
    with pytest.raises(BinderyValidationError, match="no page"):
        discover_page_files(source)


def test_discover_page_files_indexes_from_zero(mixed_name_pages: Path) -> None:
    """Page indices are zero-based in natural order."""
    pages = discover_page_files(mixed_name_pages)
    assert [p.name for p in pages] == ["page_1.png", "page_2.png", "page_10.png"]
    assert [p.index for p in pages] == [0, 1, 2]
