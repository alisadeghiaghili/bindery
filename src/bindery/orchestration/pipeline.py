"""Job orchestration: discover → transform → assemble."""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass
from pathlib import Path

from bindery.adapters.fs import discover_page_files
from bindery.adapters.images import load_image, pad_to_canvas, stamp_page_number, to_grayscale
from bindery.adapters.pdf import write_pdf
from bindery.domain.geometry import normalize_margins
from bindery.exceptions import BinderyIOError
from bindery.models.config import JobConfig
from bindery.models.page import PageFile

__all__ = [
    "JobReport",
    "assemble_job",
    "run_job",
]

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class JobReport:
    """Outcome of a completed assemble job.

    Attributes:
        output_path: Path of the written PDF.
        page_count: Number of pages written.
        pages: Discovered page files in natural order.

    Examples:
        >>> from pathlib import Path
        >>> report = JobReport(output_path=Path("book.pdf"), page_count=2, pages=())
        >>> report.page_count
        2
    """

    output_path: Path
    page_count: int
    pages: tuple[PageFile, ...]


def _transform_page(
    page: PageFile,
    config: JobConfig,
    work_dir: Path,
) -> Path:
    """Load, pad, optionally gray/stamp one page into ``work_dir``.

    Args:
        page: Source page record.
        config: Job settings.
        work_dir: Temporary directory for transformed PNGs.

    Returns:
        Path: Transformed PNG path ready for PDF embed.

    Raises:
        BinderyIOError: If load or save fails.
    """
    image = load_image(page.path)
    try:
        margins = normalize_margins(config.margins, image.size)
        image = pad_to_canvas(image, margins)
        if config.grayscale:
            image = to_grayscale(image).convert("RGB")
        if config.stamp_page_numbers:
            image = stamp_page_number(image, page_number=page.index + 1)
        out = work_dir / f"{page.index:05d}.png"
        image.save(out, format="PNG")
    finally:
        image.close()
    return out


def assemble_job(config: JobConfig) -> JobReport:
    """Run discovery + transform + PDF write for ``config``.

    Args:
        config: Immutable job description.

    Returns:
        JobReport: Output path, page count, and ordered page records.

    Raises:
        BinderyIOError: On filesystem or decode/write failures.
        BinderyValidationError: On empty source or invalid config.

    Examples:
        >>> from pathlib import Path
        >>> from PIL import Image
        >>> import tempfile
        >>> from bindery.models.config import JobConfig
        >>> root = Path(tempfile.mkdtemp())
        >>> src = root / "pages"
        >>> src.mkdir()
        >>> Image.new("RGB", (10, 10), (0, 0, 0)).save(src / "p1.png")
        >>> out = root / "book.pdf"
        >>> report = assemble_job(JobConfig(source_dir=src, output_path=out))
        >>> report.page_count
        1
    """
    pages = discover_page_files(config.source_dir)
    work_dir = config.output_path.parent / f".bindery-work-{config.output_path.stem}"
    work_dir.mkdir(parents=True, exist_ok=True)
    transformed: list[Path] = []
    try:
        for page in pages:
            transformed.append(_transform_page(page, config, work_dir))
        write_pdf(
            transformed,
            config.output_path,
            dpi=config.dpi,
            title=config.output_path.stem,
        )
    except OSError as exc:
        raise BinderyIOError(f"assemble failed: {exc}") from exc
    finally:
        for path in transformed:
            with contextlib.suppress(OSError):
                path.unlink(missing_ok=True)
        with contextlib.suppress(OSError):
            work_dir.rmdir()

    return JobReport(
        output_path=config.output_path,
        page_count=len(pages),
        pages=tuple(pages),
    )


def run_job(config: JobConfig) -> JobReport:
    """Public alias of :func:`assemble_job` for CLI/GUI callers.

    Args:
        config: Immutable job description.

    Returns:
        JobReport: Same as :func:`assemble_job`.

    Examples:
        >>> callable(run_job)
        True
    """
    return assemble_job(config)
