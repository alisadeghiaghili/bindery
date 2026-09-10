"""Page file value object."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bindery.exceptions import BinderyValidationError

__all__ = ["PageFile"]


@dataclass(frozen=True, slots=True)
class PageFile:
    """One source image destined to become a PDF page.

    Attributes:
        path: Path to the image file.
        index: Zero-based order after natural sort. Must be >= 0.

    Examples:
        >>> from pathlib import Path
        >>> page = PageFile(path=Path("page_1.png"), index=0)
        >>> page.name, page.index
        ('page_1.png', 0)
    """

    path: Path
    index: int

    def __post_init__(self) -> None:
        """Coerce path-like values and reject negative indices.

        Raises:
            BinderyValidationError: If ``index`` is negative or not an int.
        """
        if not isinstance(self.index, int) or isinstance(self.index, bool):
            raise BinderyValidationError(f"page index must be an int, got {type(self.index)!r}")
        if self.index < 0:
            raise BinderyValidationError(f"page index must be >= 0, got {self.index}")
        object.__setattr__(self, "path", Path(self.path))

    @property
    def name(self) -> str:
        """File name including extension.

        Returns:
            str: ``path.name``.
        """
        return self.path.name
