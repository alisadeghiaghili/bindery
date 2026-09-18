"""Job orchestration: discover → transform → assemble with progress and resume."""

from __future__ import annotations

import logging
import shutil
import tempfile
import time
from pathlib import Path

from bindery.adapters.bookmarks import apply_bookmarks, bookmark_titles
from bindery.adapters.fs import discover_page_files
from bindery.adapters.images import (
    crop_image,
    fit_image_to_page,
    load_image,
    pad_to_canvas,
    rotate_image,
    save_page_image,
    stamp_page_number,
    to_grayscale,
)
from bindery.adapters.pdf import write_pdf
from bindery.domain.geometry import normalize_margins
from bindery.exceptions import BinderyIOError, BinderyValidationError
from bindery.models.config import JobConfig
from bindery.models.crop import MarginSpec
from bindery.models.jobfile import SourceSpec
from bindery.models.page import PageFile
from bindery.models.page_size import parse_page_size
from bindery.orchestration.manifest import (
    JobReport,
    ResumeManifest,
    config_fingerprint,
    manifest_path_for,
    page_identity,
)
from bindery.orchestration.progress import ProgressCallback, ProgressEvent

__all__ = [
    "JobReport",
    "assemble_job",
    "discover_job_pages",
    "run_job",
    "select_pages",
    "transform_page",
]

logger = logging.getLogger(__name__)

#: Minimum bottom padding (px) reserved for footer stamps when user margins are thinner.
_STAMP_FOOTER_BAND = 16


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


def select_pages(pages: list[PageFile], page_names: tuple[str, ...] | None) -> list[PageFile]:
    """Filter and reorder discovered pages by explicit file names.

    Args:
        pages: Naturally sorted discovered pages.
        page_names: Optional explicit order of source file names.

    Returns:
        list[PageFile]: Selected pages with contiguous zero-based indices.

    Raises:
        BinderyValidationError: If a requested name is missing.

    Examples:
        >>> callable(select_pages)
        True
    """
    if page_names is None:
        return list(pages)
    by_name = {page.name: page for page in pages}
    selected: list[PageFile] = []
    for index, name in enumerate(page_names):
        if name not in by_name:
            raise BinderyValidationError(f"page not found in source: {name}")
        source_page = by_name[name]
        selected.append(PageFile(path=source_page.path, index=index))
    return selected


def _effective_source_specs(config: JobConfig) -> tuple[SourceSpec, ...]:
    """Return source specs for discovery from JobConfig.

    Args:
        config: Active job settings.

    Returns:
        tuple[SourceSpec, ...]: Specs in assemble order.

    Examples:
        >>> callable(_effective_source_specs)
        True
    """
    if config.sources is not None:
        return config.sources
    specs: list[SourceSpec] = [SourceSpec(path=config.source_dir, page_names=config.page_names)]
    specs.extend(SourceSpec(path=path) for path in config.extra_sources)
    return tuple(specs)


def discover_job_pages(config: JobConfig) -> tuple[list[PageFile], list[int], list[str]]:
    """Discover pages across all job sources with chapter boundaries.

    Args:
        config: Active job settings.

    Returns:
        tuple: ``(pages, chapter_starts, chapter_labels)``.

    Raises:
        BinderyValidationError: If a requested page name is missing.

    Examples:
        >>> callable(discover_job_pages)
        True
    """
    chapter_selected: list[list[PageFile]] = []
    chapter_labels: list[str] = []
    for spec in _effective_source_specs(config):
        discovered = discover_page_files(spec.path)
        selected = select_pages(discovered, spec.page_names)
        if spec.exclude:
            excluded = set(spec.exclude)
            selected = [page for page in selected if page.name not in excluded]
        chapter_selected.append(selected)
        chapter_labels.append(spec.path.name or str(spec.path))

    if config.exclude_names:
        global_excluded = set(config.exclude_names)
        chapter_selected = [
            [page for page in chapter if page.name not in global_excluded]
            for chapter in chapter_selected
        ]

    pages: list[PageFile] = []
    chapter_starts: list[int] = []
    for chapter in chapter_selected:
        chapter_starts.append(len(pages))
        for page in chapter:
            pages.append(PageFile(path=page.path, index=len(pages)))
    return pages, chapter_starts, chapter_labels


def transform_page(page: PageFile, config: JobConfig, work_dir: Path) -> Path:
    """Apply crop/rotate/pad/stamp/gray/page-size and write one page file.

    Args:
        page: Source page record.
        config: Job settings.
        work_dir: Directory that receives the transformed page file.

    Returns:
        Path: Written PNG or JPEG path.

    Raises:
        BinderyIOError: If load/save fails.
        BinderyValidationError: If crop does not fit the source image.

    Examples:
        >>> callable(transform_page)
        True
    """
    image = load_image(page.path)
    try:
        if config.crop is not None:
            image = crop_image(image, config.crop)
        if config.rotate:
            image = rotate_image(image, config.rotate)

        margins = normalize_margins(config.margins, image.size)
        if config.stamp_page_numbers and margins.bottom < _STAMP_FOOTER_BAND:
            margins = MarginSpec(
                left=margins.left,
                top=margins.top,
                right=margins.right,
                bottom=_STAMP_FOOTER_BAND,
            )
        image = pad_to_canvas(image, margins)
        if config.stamp_page_numbers:
            image = stamp_page_number(image, page_number=page.index + 1)
        if config.grayscale:
            image = to_grayscale(image)

        page_size = parse_page_size(config.page_size)
        if page_size is not None:
            image = fit_image_to_page(image, page_size, config.dpi)

        out = work_dir / f"{page.index:05d}"
        written = save_page_image(
            image,
            out,
            compress=config.compress,
            jpeg_quality=config.jpeg_quality,
        )
    finally:
        image.close()
    return written


# Back-compat private alias used by older tests.
_transform_page = transform_page


def _should_skip(config: JobConfig, page_identities: list[dict[str, int | str]]) -> bool:
    """Return True when output is up to date and force is off.

    Args:
        config: Active job settings.
        page_identities: Ordered page content identities for this run.

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
        config, page_identities
    ) and manifest.page_count == len(page_identities)


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
        BinderyValidationError: On empty source, missing page names, or invalid config.

    Examples:
        >>> callable(assemble_job)
        True
    """
    started = time.perf_counter()
    pages, chapter_starts, chapter_labels = discover_job_pages(config)
    page_identities = [page_identity(page.path) for page in pages]
    _emit(
        on_progress,
        ProgressEvent(
            stage="discover",
            completed=len(pages),
            total=len(pages),
            message=f"found {len(pages)} pages",
        ),
    )

    fingerprint = config_fingerprint(config, page_identities)
    if _should_skip(config, page_identities):
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

    work_dir = Path(tempfile.mkdtemp(prefix=f"bindery-{config.output_path.stem}-"))
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
            transformed.append(transform_page(page, config, work_dir))
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
            title=config.title or config.output_path.stem,
            author=config.author,
        )
        titles = bookmark_titles(
            config.bookmark_mode,
            [page.name for page in pages],
            chapter_starts,
            chapter_labels,
        )
        if titles is not None:
            apply_bookmarks(config.output_path, titles)
    except OSError as exc:
        raise BinderyIOError(f"assemble failed: {exc}") from exc
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

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
