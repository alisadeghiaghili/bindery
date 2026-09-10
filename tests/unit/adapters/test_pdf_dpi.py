"""PDF page physical size must honor the requested dpi."""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from pypdf import PdfReader

from bindery.adapters.pdf import write_pdf
from bindery.models.config import JobConfig
from bindery.models.crop import MarginSpec
from bindery.orchestration.pipeline import run_job


def _px_to_pt(pixels: float, dpi: int) -> float:
    return pixels * 72.0 / dpi


def test_write_pdf_honors_dpi_in_mediabox(tmp_path: Path) -> None:
    """A 100x50 image at 100 dpi becomes 72x36 pt pages (not the 96 dpi default)."""
    image_path = tmp_path / "p.png"
    Image.new("RGB", (100, 50), (0, 0, 0)).save(image_path)
    out = tmp_path / "book.pdf"
    write_pdf([image_path], out, dpi=100)
    reader = PdfReader(out)
    box = reader.pages[0].mediabox
    assert abs(float(box.width) - _px_to_pt(100, 100)) < 0.5
    assert abs(float(box.height) - _px_to_pt(50, 100)) < 0.5


def test_write_pdf_dpi_96_matches_default_layout(tmp_path: Path) -> None:
    """96 dpi remains the compatibility default size."""
    image_path = tmp_path / "p.png"
    Image.new("RGB", (96, 96), (0, 0, 0)).save(image_path)
    out = tmp_path / "book.pdf"
    write_pdf([image_path], out, dpi=96)
    box = PdfReader(out).pages[0].mediabox
    assert abs(float(box.width) - 72.0) < 0.5
    assert abs(float(box.height) - 72.0) < 0.5


def test_run_job_dpi_affects_physical_size(tmp_path: Path) -> None:
    """End-to-end job respects JobConfig.dpi after padding."""
    source = tmp_path / "pages"
    source.mkdir()
    Image.new("RGB", (100, 100), (10, 20, 30)).save(source / "a.png")
    out = tmp_path / "book.pdf"
    run_job(
        JobConfig(
            source_dir=source,
            output_path=out,
            dpi=50,
            margins=MarginSpec.uniform(10),
        )
    )
    box = PdfReader(out).pages[0].mediabox
    expected = 120 * 72.0 / 50
    assert abs(float(box.width) - expected) < 0.5
    assert abs(float(box.height) - expected) < 0.5
