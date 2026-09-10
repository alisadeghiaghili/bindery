"""Tests for PDF assembly adapter."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader

from bindery.adapters.pdf import write_pdf
from bindery.exceptions import BinderyIOError, BinderyValidationError


def _make_pngs(directory: Path, count: int) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for i in range(count):
        path = directory / f"p{i + 1}.png"
        Image.new("RGB", (20, 30), (i * 10, 0, 0)).save(path)
        paths.append(path)
    return paths


def test_write_pdf_page_count(tmp_path: Path) -> None:
    """Assembled PDF has one page per source image."""
    pngs = _make_pngs(tmp_path / "in", 3)
    out = tmp_path / "out.pdf"
    write_pdf(pngs, out, dpi=150, title="Demo")
    reader = PdfReader(out)
    assert len(reader.pages) == 3


def test_write_pdf_empty_input(tmp_path: Path) -> None:
    """Empty image list is rejected before writing."""
    with pytest.raises(BinderyValidationError, match="at least one"):
        write_pdf([], tmp_path / "out.pdf")


def test_write_pdf_creates_parent_dirs(tmp_path: Path) -> None:
    """Missing output parent directories are created."""
    pngs = _make_pngs(tmp_path / "in", 1)
    out = tmp_path / "deep" / "nested" / "book.pdf"
    write_pdf(pngs, out)
    assert out.is_file()


def test_write_pdf_metadata_title(tmp_path: Path) -> None:
    """Title metadata is embedded when provided."""
    pngs = _make_pngs(tmp_path / "in", 1)
    out = tmp_path / "book.pdf"
    write_pdf(pngs, out, title="My Book")
    reader = PdfReader(out)
    meta = reader.metadata
    assert meta is not None
    assert "My Book" in (meta.title or meta.get("/Title") or "")


def test_write_pdf_missing_source_image(tmp_path: Path) -> None:
    """A missing page image raises BinderyIOError."""
    missing = tmp_path / "gone.png"
    with pytest.raises(BinderyIOError, match="cannot read"):
        write_pdf([missing], tmp_path / "out.pdf")


def test_write_pdf_writes_once_valid_pdf_header(tmp_path: Path) -> None:
    """Output starts with the PDF magic header."""
    pngs = _make_pngs(tmp_path / "in", 2)
    out = tmp_path / "book.pdf"
    write_pdf(pngs, out)
    assert out.read_bytes()[:5] == b"%PDF-"
