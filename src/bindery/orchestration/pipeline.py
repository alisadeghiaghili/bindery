"""Job orchestration: discover → transform → assemble with progress and resume."""

from __future__ import annotations

import contextlib
import logging
import time
from pathlib import Path

from bindery.adapters.fs import discover_page_files
from bindery.adapters.images import load_image, pad_to_canvas, stamp_page_number, to_grayscale
from bindery.adapters.pdf import write_pdf
from bindery.domain.geometry import normalize_margins
from bindery.exceptions import BinderyIOError
from bindery.models.config import JobConfig
from bindery.models.page import PageFile
from bindery.orchestration.manifest import (
    JobReport,
    ResumeManifest,
    config_fingerprint,
    manifest_path_for,
)
from bindery.orchestration.progress import ProgressCallback, ProgressEvent

__all__ = [
    "JobReport",
    "assemble_job",
    "run_job",
]

logger = logging.getLogger(__name__)


def _emit(callback: ProgressCallback | None, event: ProgressEvent) -> None:
    """Deliver ``event`` to ``callback`` if provided.

    Args:
        callback: Optional progress sink.
        event: Event to deliver.

    Examples:
        >>> _emit(None, ProgressEvent(stage="done", completed=1, total=1))
    """
    if callback is None:
        return
    callback(event)


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


def _should_skip(config: JobConfig, page_names: list[str]) -> bool:
    """Return True when output is up to date and force is off.

    Args:
        config: Active job settings.
        page_names: Ordered page names for this run.

    Returns:
        bool: True if the existing PDF can be reused.
    """
    if config.force:
        return False
    if not config.output_path.is_file():
        return False
    manifest = ResumeManifest.load(manifest_path_for(config.output_path))
    if manifest is None:
        return False
    return manifest.fingerprint == config_fingerprint(
        config, page_names
    ) and manifest.page_count == len(page_names)


def assemble_job(
    config: JobConfig,
    *,
    on_progress: ProgressCallback | None = None,
) -> JobReport:
    """Run discovery + transform + PDF write for ``config``.

    Args:
        config: Immutable job description.
        on_progress: Optional callback invoked with :class:`ProgressEvent`s.

    Returns:
        JobReport: Output path, page count, ordered pages, and skip flag.

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
        >>> events = []
        >>> report = assemble_job(
        ...     JobConfig(source_dir=src, output_path=out),
        ...     on_progress=events.append,
        ... )
        >>> report.page_count, report.skipped
        (1, False)
        >>> any(e.stage == "done" for e in events)
        True
    """
    started = time.perf_counter()
    pages = discover_page_files(config.source_dir)
    page_names = [p.name for p in pages]
    _emit(
        on_progress,
        ProgressEvent(
            stage="discover",
            completed=len(pages),
            total=len(pages),
            message=f"found {len(pages)} pages",
        ),
    )

    fingerprint = config_fingerprint(config, page_names)
    if _should_skip(config, page_names):
        logger.info("skipping rebuild; output is up to date: %s", config.output_path)
        _emit(
            on_progress,
            ProgressEvent(
                stage="skipped",
                completed=len(pages),
                total=len(pages),
                message="output up to date",
            ),
        )
        return JobReport(
            output_path=config.output_path,
            page_count=len(pages),
            pages=tuple(pages),
            skipped=True,
        )

    work_dir = config.output_path.parent / f".bindery-work-{config.output_path.stem}"
    work_dir.mkdir(parents=True, exist_ok=True)
    transformed: list[Path] = []
    try:
        for page in pages:
            _emit(
                on_progress,
                ProgressEvent(
                    stage="transform",
                    completed=page.index,
                    total=len(pages),
                    current=page.name,
                ),
            )
            transformed.append(_transform_page(page, config, work_dir))
        _emit(
            on_progress,
            ProgressEvent(
                stage="transform",
                completed=len(pages),
                total=len(pages),
                current=None,
            ),
        )
        _emit(
            on_progress,
            ProgressEvent(
                stage="assemble",
                completed=0,
                total=1,
                current=config.output_path.name,
            ),
        )
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

    ResumeManifest(fingerprint=fingerprint, page_count=len(pages)).save(
        manifest_path_for(config.output_path)
    )
    elapsed = time.perf_counter() - started
    logger.info("wrote %s pages=%d elapsed_s=%.3f", config.output_path, len(pages), elapsed)
    _emit(
        on_progress,
        ProgressEvent(
            stage="done",
            completed=len(pages),
            total=len(pages),
            message=f"{len(pages)} pages in {elapsed:.2f}s",
        ),
    )
    return JobReport(
        output_path=config.output_path,
        page_count=len(pages),
        pages=tuple(pages),
        skipped=False,
    )


def run_job(
    config: JobConfig,
    *,
    on_progress: ProgressCallback | None = None,
) -> JobReport:
    """Public alias of :func:`assemble_job` for CLI/GUI callers.

    Args:
        config: Immutable job description.
        on_progress: Optional progress callback.

    Returns:
        JobReport: Same as :func:`assemble_job`.

    Examples:
        >>> callable(run_job)
        True
    """
    return assemble_job(config, on_progress=on_progress)
