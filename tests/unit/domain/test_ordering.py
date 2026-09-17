"""Tests for natural page ordering."""

from __future__ import annotations

from bindery.domain.ordering import natural_sort_key, sort_page_names


def test_natural_sort_key_orders_digit_runs_as_integers() -> None:
    """Numeric chunks compare as integers, not lexicographic strings."""
    assert natural_sort_key("page_2.png") < natural_sort_key("page_10.png")
    assert natural_sort_key("page_9.png") < natural_sort_key("page_10.png")


def test_sort_page_names_orders_naturally() -> None:
    """sort_page_names returns natural order."""
    assert sort_page_names(["page_10.png", "page_2.png", "page_1.png"]) == [
        "page_1.png",
        "page_2.png",
        "page_10.png",
    ]


def test_sort_page_names_empty() -> None:
    """Empty input yields empty output."""
    assert sort_page_names([]) == []


def test_sort_page_names_is_total_for_zero_padding() -> None:
    """Equivalent numeric names still have a deterministic order."""
    names = ["page_2.png", "page_02.png", "page_1.png"]
    assert sort_page_names(names) == ["page_1.png", "page_02.png", "page_2.png"]
    assert natural_sort_key("page_02.png") != natural_sort_key("page_2.png")


def test_natural_sort_key_case_insensitive_text() -> None:
    """Text chunks are lowercased for comparison."""
    assert natural_sort_key("Page_2.png") < natural_sort_key("page_10.png")
