"""Integration tests: discover → transform → assemble."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from bindery.models.config import JobConfig
from bindery.orchestration.pipeline import assemble_job, run_job


def test_run_job_end_to_end(rgb_pages: Path, tmp_path: Path) -> None:
    """A small folder of PNGs becomes a valid multi-page PDF."""
    output = tmp_path / "book.pdf"
    config = JobConfig(
        source_dir=rgb_pages,
        output_path=output,
        grayscale=True,
        stamp_page_numbers=True,
    )
    report = run_job(config)
    assert output.is_file()
    reader = PdfReader(output)
    assert len(reader.pages) == 3
    assert report.page_count == 3
    assert report.output_path == output


def test_run_job_respects_natural_order(mixed_name_pages: Path, tmp_path: Path) -> None:
    """Page order follows natural sort, not lexicographic."""
    output = tmp_path / "ordered.pdf"
    config = JobConfig(source_dir=mixed_name_pages, output_path=output)
    report = run_job(config)
    assert [p.name for p in report.pages] == ["page_1.png", "page_2.png", "page_10.png"]


def test_assemble_job_without_stamps(rgb_pages: Path, tmp_path: Path) -> None:
    """Stamps off still produces a PDF."""
    output = tmp_path / "plain.pdf"
    config = JobConfig(source_dir=rgb_pages, output_path=output, stamp_page_numbers=False)
    report = assemble_job(config)
    assert report.page_count == 3
