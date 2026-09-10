"""Tests for natural ordering of page filenames."""

from __future__ import annotations

import pytest

from bindery.domain.ordering import natural_sort_key, sort_page_names


@pytest.mark.parametrize(
    ("names", "expected"),
    [
        (["page_10.png", "page_2.png", "page_1.png"], ["page_1.png", "page_2.png", "page_10.png"]),
        (["img9.jpg", "img10.jpg", "img1.jpg"], ["img1.jpg", "img9.jpg", "img10.jpg"]),
        (["2.png", "10.png", "1.png"], ["1.png", "2.png", "10.png"]),
        (["a2b10.png", "a2b2.png", "a2b1.png"], ["a2b1.png", "a2b2.png", "a2b10.png"]),
        (["cover.png", "page_1.png"], ["cover.png", "page_1.png"]),
        ([], []),
    ],
)
def test_sort_page_names_natural(names: list[str], expected: list[str]) -> None:
    """Numeric runs sort as integers, not as raw text."""
    assert sort_page_names(names) == expected


def test_sort_does_not_mutate_input() -> None:
    """Sorting returns a new list; the caller sequence is unchanged."""
    names = ["page_10.png", "page_2.png"]
    original = list(names)
    result = sort_page_names(names)
    assert names == original
    assert result == ["page_2.png", "page_10.png"]


def test_natural_sort_key_is_deterministic() -> None:
    """Equal names produce equal keys."""
    assert natural_sort_key("page_03.png") == natural_sort_key("page_03.png")


def test_zero_padding_does_not_reorder_same_number() -> None:
    """``page_01`` and ``page_1`` compare equal numerically (stable by name)."""
    names = ["page_1.png", "page_01.png", "page_2.png"]
    result = sort_page_names(names)
    assert result[-1] == "page_2.png"
    assert set(result[:2]) == {"page_1.png", "page_01.png"}
