"""Named PDF page sizes in PDF points (1/72 inch)."""

from __future__ import annotations

from bindery.exceptions import BinderyValidationError

__all__ = ["PAGE_PRESETS", "parse_page_size"]

#: Portrait page boxes in points ``(width, height)``.
PAGE_PRESETS: dict[str, tuple[float, float]] = {
    "a4": (595.276, 841.89),
    "letter": (612.0, 792.0),
}


def parse_page_size(value: str | None) -> tuple[float, float] | None:
    """Parse a page-size token into PDF points.

    Args:
        value: ``None`` (keep source-derived geometry), a preset name
            (``a4`` / ``letter``), or ``WIDTHxHEIGHT`` in points
            (``595x842`` or ``595.28x841.89``).

    Returns:
        tuple[float, float] | None: ``(width_pt, height_pt)`` or ``None``.

    Raises:
        BinderyValidationError: If the token is not a preset or ``WxH``.

    Examples:
        >>> parse_page_size("a4")[1] > 800
        True
        >>> parse_page_size("10x20")
        (10.0, 20.0)
        >>> parse_page_size(None) is None
        True
    """
    if value is None:
        return None
    token = value.strip().lower()
    if not token:
        return None
    if token in PAGE_PRESETS:
        return PAGE_PRESETS[token]
    if "x" not in token:
        raise BinderyValidationError(
            f"page-size must be a4, letter, or WIDTHxHEIGHT pt, got {value!r}"
        )
    width_s, _, height_s = token.partition("x")
    try:
        width = float(width_s)
        height = float(height_s)
    except ValueError:
        raise BinderyValidationError(
            f"page-size must be a4, letter, or WIDTHxHEIGHT pt, got {value!r}"
        ) from None
    if width <= 0 or height <= 0:
        raise BinderyValidationError(f"page-size dimensions must be positive, got {value!r}")
    return (width, height)
