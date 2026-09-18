"""Job configuration for a single bindery run."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from bindery.exceptions import BinderyValidationError
from bindery.models.crop import CropBox, MarginSpec
from bindery.models.jobfile import SourceSpec
from bindery.models.page_size import parse_page_size

__all__ = ["JobConfig"]

_DEFAULT_DPI = 300
_ALLOWED_ROTATE = frozenset({0, 90, 180, 270})
_ALLOWED_COMPRESS = frozenset({"lossless", "jpeg"})
_ALLOWED_BOOKMARKS = frozenset({"none", "filenames", "chapters"})


@dataclass(frozen=True, slots=True)
class JobConfig:
    """Immutable description of one assemble job.

    Attributes:
        source_dir: Primary directory containing page images.
        output_path: Destination PDF path (parent dirs may not exist yet).
        margins: Padding applied around each page.
        grayscale: Convert pages to 8-bit grayscale before writing.
        stamp_page_numbers: Draw a footer page number on each page.
        dpi: Resolution metadata written into the PDF. Must be > 0.
        force: Rebuild even when a matching resume manifest says the output is current.
        title: Optional PDF document title. ``None`` uses the output stem.
        author: Optional PDF document author metadata.
        crop: Optional crop rectangle in source pixels (before rotate/pad).
        rotate: Clockwise rotation in degrees; one of ``0, 90, 180, 270``.
        page_size: ``None`` keeps source-derived geometry; otherwise preset
            (``a4``/``letter``) or ``WIDTHxHEIGHT`` in PDF points.
        compress: ``lossless`` (PNG embed) or ``jpeg`` (JPEG embed).
        jpeg_quality: JPEG quality 1-95 when ``compress='jpeg'``.
        page_names: Optional explicit assemble order (subset of source names)
            when ``sources`` is ``None``.
        extra_sources: Additional directories appended after ``source_dir``.
        sources: Full multi-source specs (job files). When set, overrides
            ``source_dir``/``extra_sources``/``page_names`` discovery.
        bookmark_mode: ``none``, ``filenames``, or ``chapters``.

    Examples:
        >>> from pathlib import Path
        >>> cfg = JobConfig(source_dir=Path("pages"), output_path=Path("book.pdf"))
        >>> cfg.bookmark_mode, cfg.extra_sources
        ('none', ())
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
    crop: CropBox | None = None
    rotate: int = 0
    page_size: str | None = None
    compress: str = "lossless"
    jpeg_quality: int = 85
    page_names: tuple[str, ...] | None = None
    exclude_names: tuple[str, ...] | None = None
    extra_sources: tuple[Path, ...] = ()
    sources: tuple[SourceSpec, ...] | None = None
    bookmark_mode: str = "none"

    def __post_init__(self) -> None:
        """Coerce paths, metadata, rotation, compress, and page size.

        Raises:
            BinderyValidationError: On invalid dpi, paths, rotate, compress,
                jpeg quality, or page-size token.
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

        rotate = self.rotate
        if isinstance(rotate, bool) or not isinstance(rotate, int) or rotate not in _ALLOWED_ROTATE:
            raise BinderyValidationError(
                f"rotate must be one of {sorted(_ALLOWED_ROTATE)}, got {rotate!r}"
            )
        object.__setattr__(self, "rotate", int(rotate) % 360)

        compress = str(self.compress).strip().lower()
        if compress not in _ALLOWED_COMPRESS:
            raise BinderyValidationError(
                f"compress must be one of {sorted(_ALLOWED_COMPRESS)}, got {self.compress!r}"
            )
        object.__setattr__(self, "compress", compress)

        quality = self.jpeg_quality
        if isinstance(quality, bool) or not isinstance(quality, int):
            raise BinderyValidationError(f"jpeg_quality must be an int, got {type(quality)!r}")
        if quality < 1 or quality > 95:
            raise BinderyValidationError(f"jpeg_quality must be in 1..95, got {quality}")

        if self.page_size is not None:
            parsed = parse_page_size(self.page_size)
            if parsed is None:
                object.__setattr__(self, "page_size", None)
            else:
                object.__setattr__(self, "page_size", self.page_size.strip().lower())

        if self.page_names is not None:
            names = tuple(self.page_names)
            if any(not isinstance(n, str) or not n for n in names):
                raise BinderyValidationError("page_names must be non-empty file names")
            if len(set(names)) != len(names):
                raise BinderyValidationError("page_names must not contain duplicates")
            object.__setattr__(self, "page_names", names)

        if self.exclude_names is not None:
            excl = tuple(str(n) for n in self.exclude_names)
            if any(not n for n in excl):
                raise BinderyValidationError("exclude_names must be non-empty")
            object.__setattr__(self, "exclude_names", excl)

        extras = tuple(Path(p) for p in self.extra_sources)
        object.__setattr__(self, "extra_sources", extras)

        if self.sources is not None:
            specs = tuple(self.sources)
            if not specs:
                raise BinderyValidationError("sources must be non-empty when provided")
            object.__setattr__(self, "sources", specs)
            primary = specs[0].path
            object.__setattr__(self, "source_dir", primary)
            object.__setattr__(
                self,
                "extra_sources",
                tuple(spec.path for spec in specs[1:]),
            )

        bookmark_mode = str(self.bookmark_mode).strip().lower()
        if bookmark_mode not in _ALLOWED_BOOKMARKS:
            raise BinderyValidationError(
                f"bookmark_mode must be one of {sorted(_ALLOWED_BOOKMARKS)}, got {self.bookmark_mode!r}"
            )
        object.__setattr__(self, "bookmark_mode", bookmark_mode)

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
