"""Filesystem discovery of page images."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

from bindery.domain.ordering import natural_sort_key
from bindery.exceptions import BinderyIOError, BinderyValidationError
from bindery.models.page import PageFile

__all__ = [
    "IMAGE_SUFFIXES",
    "discover_page_files",
    "list_image_paths",
]

#: Lowercase suffixes treated as page images.
IMAGE_SUFFIXES: frozenset[str] = frozenset(
    {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}
)


def list_image_paths(source_dir: Path) -> list[Path]:
    """List image files in ``source_dir`` using natural sort.

    Args:
        source_dir: Directory that must already exist.

    Returns:
        list: Sorted image paths. Non-image files are skipped.

    Raises:
        BinderyIOError: If ``source_dir`` does not exist or is not a directory.

    Examples:
        >>> from pathlib import Path
        >>> # doctest requires a real directory; see tests.
        >>> callable(list_image_paths)
        True
    """
    directory = Path(source_dir)
    if not directory.exists():
        raise BinderyIOError(f"source directory does not exist: {directory}")
    if not directory.is_dir():
        raise BinderyIOError(f"source is not a directory: {directory}")

    names: Iterable[str] = (
        entry.name
        for entry in directory.iterdir()
        if entry.is_file() and entry.suffix.lower() in IMAGE_SUFFIXES
    )
    ordered: Sequence[str] = sorted(names, key=natural_sort_key)
    return [directory / name for name in ordered]


def discover_page_files(source_dir: Path) -> list[PageFile]:
    """Discover page images and assign zero-based natural-order indices.

    Args:
        source_dir: Directory containing page images.

    Returns:
        list: ``PageFile`` records in natural sort order.

    Raises:
        BinderyIOError: If the directory is missing or not a directory.
        BinderyValidationError: If no image files are present.

    Examples:
        >>> callable(discover_page_files)
        True
    """
    paths = list_image_paths(source_dir)
    if not paths:
        raise BinderyValidationError(
            f"no page images found in {source_dir} (suffixes: {sorted(IMAGE_SUFFIXES)})"
        )
    return [PageFile(path=path, index=index) for index, path in enumerate(paths)]
