"""Job configuration for a single bindery run."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from bindery.exceptions import BinderyValidationError
from bindery.models.crop import MarginSpec

__all__ = ["JobConfig"]

_DEFAULT_DPI = 300


@dataclass(frozen=True, slots=True)
class JobConfig:
    """Immutable description of one assemble job.

    Attributes:
        source_dir: Directory containing page images.
        output_path: Destination PDF path (parent dirs may not exist yet).
        margins: Padding applied around each page.
        grayscale: Convert pages to 8-bit grayscale before writing.
        stamp_page_numbers: Draw a footer page number on each page.
        dpi: Resolution metadata written into the PDF. Must be > 0.
        force: Rebuild even when a matching resume manifest says the output is current.
        title: Optional PDF document title. ``None`` uses the output stem.
        author: Optional PDF document author metadata.

    Examples:
        >>> from pathlib import Path
        >>> cfg = JobConfig(source_dir=Path("pages"), output_path=Path("book.pdf"))
        >>> cfg.dpi, cfg.grayscale, cfg.force
        (300, False, False)
        >>> cfg.title is None and cfg.author is None
        True
    """

    source_dir: Path
    output_path: Path
    margins: MarginSpec = field(default_factory=MarginSpec)
    grayscale: bool = False
    stamp_page_numbers: bool = False
    dpi: int = _DEFAULT_DPI
    force: bool = False
    title: str | None = None
    author: str | None = None

    def __post_init__(self) -> None:
        """Coerce paths, metadata strings, and numeric fields.

        Raises:
            BinderyValidationError: If dpi is non-positive or source equals output.
        """
        source = Path(self.source_dir)
        output = Path(self.output_path)
        object.__setattr__(self, "source_dir", source)
        object.__setattr__(self, "output_path", output)
        object.__setattr__(self, "title", self._normalize_metadata(self.title))
        object.__setattr__(self, "author", self._normalize_metadata(self.author))

        if not isinstance(self.dpi, int) or isinstance(self.dpi, bool):
            raise BinderyValidationError(f"dpi must be an int, got {type(self.dpi)!r}")
        if self.dpi <= 0:
            raise BinderyValidationError(f"dpi must be positive, got {self.dpi}")

        if source.resolve() == output.resolve():
            raise BinderyValidationError(f"output must differ from source_dir; both are {source}")

    @staticmethod
    def _normalize_metadata(value: str | None) -> str | None:
        """Strip metadata strings; empty values become ``None``.

        Args:
            value: Raw title or author from CLI/GUI/API.

        Returns:
            str | None: Normalized metadata, or ``None`` when blank.

        Examples:
            >>> JobConfig._normalize_metadata("  Book  ")
            'Book'
            >>> JobConfig._normalize_metadata("   ") is None
            True
        """
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None
