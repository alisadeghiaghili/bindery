"""Natural ordering for page filenames."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

__all__ = [
    "natural_sort_key",
    "sort_page_names",
]

_DIGIT_RUN = re.compile(r"(\d+)")


def natural_sort_key(name: str) -> tuple[tuple[int, object], ...]:
    """Build a sort key that orders digit runs as integers.

    The final ``(2, name)`` term makes the key total: names that collapse to
    the same numeric structure (``page_2.png`` vs ``page_02.png``) still sort
    deterministically.

    Args:
        name: File name or stem, e.g. ``"page_10.png"``.

    Returns:
        tuple: Sequence of ``(0, str)`` for text chunks, ``(1, int)`` for
        digit runs, and ``(2, str)`` for the original name.

    Examples:
        >>> natural_sort_key("page_2.png") < natural_sort_key("page_10.png")
        True
        >>> natural_sort_key("page_02.png") < natural_sort_key("page_2.png")
        True
    """
    parts: list[tuple[int, object]] = []
    for chunk in _DIGIT_RUN.split(name):
        if chunk == "":
            continue
        if chunk.isdigit():
            parts.append((1, int(chunk)))
        else:
            parts.append((0, chunk.lower()))
    parts.append((2, name))
    return tuple(parts)


def sort_page_names(names: Sequence[str] | Iterable[str]) -> list[str]:
    """Return names ordered by natural sort (stable, non-mutating).

    Args:
        names: Iterable of page file names.

    Returns:
        list: New list sorted by :func:`natural_sort_key`. Empty input yields
        an empty list.

    Examples:
        >>> sort_page_names(["page_10.png", "page_2.png", "page_1.png"])
        ['page_1.png', 'page_2.png', 'page_10.png']
        >>> sort_page_names(["page_2.png", "page_02.png", "page_1.png"])
        ['page_1.png', 'page_02.png', 'page_2.png']
    """
    return sorted(names, key=natural_sort_key)
