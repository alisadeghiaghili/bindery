"""Tests for domain input validation helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from bindery.domain.validate import ensure_positive_size, ensure_source_output_distinct
from bindery.exceptions import BinderyValidationError


def test_ensure_positive_size_accepts_valid() -> None:
    """Positive width/height pass through."""
    assert ensure_positive_size((3, 4), context="image") == (3, 4)


@pytest.mark.parametrize("size", [(0, 1), (1, 0), (-1, 2), (2, -1), (0, 0)])
def test_ensure_positive_size_rejects_invalid(size: tuple[int, int]) -> None:
    """Any non-positive dimension raises with context in the message."""
    with pytest.raises(BinderyValidationError, match="image"):
        ensure_positive_size(size, context="image")


def test_ensure_source_output_distinct_ok(tmp_path: Path) -> None:
    """Different source and output paths are accepted."""
    ensure_source_output_distinct(tmp_path / "pages", tmp_path / "book.pdf")


def test_ensure_source_output_distinct_rejects_identical(tmp_path: Path) -> None:
    """Identical source and output paths are rejected."""
    target = tmp_path / "same"
    with pytest.raises(BinderyValidationError, match="output"):
        ensure_source_output_distinct(target, target)
