"""Input validation helpers (pure)."""

from __future__ import annotations

from pathlib import Path

from bindery.exceptions import BinderyValidationError

__all__ = [
    "ensure_positive_size",
    "ensure_source_output_distinct",
]


def ensure_positive_size(size: tuple[int, int], *, context: str = "image") -> tuple[int, int]:
    """Assert that a ``(width, height)`` pair is strictly positive.

    Args:
        size: Candidate ``(width, height)`` in pixels.
        context: Short label used in the error message (e.g. ``"image"``).

    Returns:
        tuple: The same ``size`` when valid.

    Raises:
        BinderyValidationError: If either dimension is not a positive int.

    Examples:
        >>> ensure_positive_size((2, 3), context="image")
        (2, 3)
    """
    width, height = size
    for name, value in (("width", width), ("height", height)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise BinderyValidationError(f"{context} {name} must be an int, got {type(value)!r}")
        if value <= 0:
            raise BinderyValidationError(f"{context} {name} must be positive, got {value}")
    return (width, height)


def ensure_source_output_distinct(source: Path, output: Path) -> None:
    """Reject jobs where the output path equals the source path.

    Args:
        source: Source directory or file.
        output: Destination PDF path.

    Raises:
        BinderyValidationError: If the two paths are equal.

    Examples:
        >>> from pathlib import Path
        >>> ensure_source_output_distinct(Path("pages"), Path("book.pdf"))
    """
    if Path(source) == Path(output):
        raise BinderyValidationError(f"output must differ from source_dir; both are {source}")
