"""Tests for page workbench features: crop, rotate, page size, compress, select."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader

from bindery.cli import main
from bindery.exceptions import BinderyValidationError
from bindery.models.config import JobConfig
from bindery.models.crop import CropBox, MarginSpec
from bindery.models.page import PageFile
from bindery.models.page_size import parse_page_size
from bindery.orchestration.pipeline import run_job, select_pages, transform_page


def _write_png(path: Path, size: tuple[int, int], color: tuple[int, int, int]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)
    return path


def _pages(tmp_path: Path) -> Path:
    source = tmp_path / "pages"
    _write_png(source / "page_1.png", (40, 60), (200, 0, 0))
    _write_png(source / "page_2.png", (40, 60), (0, 200, 0))
    _write_png(source / "page_10.png", (40, 60), (0, 0, 200))
    return source


def test_parse_page_size_presets() -> None:
    """a4/letter presets and custom WxH parse to points."""
    a4 = parse_page_size("a4")
    assert a4 is not None
    assert a4[0] == pytest.approx(595.276, rel=0.01)
    letter = parse_page_size("LETTER")
    assert letter == (612.0, 792.0)
    assert parse_page_size("10x20") == (10.0, 20.0)
    assert parse_page_size(None) is None


def test_parse_page_size_rejects_bad_tokens() -> None:
    """Invalid page-size tokens raise validation errors."""
    with pytest.raises(BinderyValidationError):
        parse_page_size("tabloid")
    with pytest.raises(BinderyValidationError):
        parse_page_size("0x10")


def test_job_config_rejects_bad_rotate_and_compress(tmp_path: Path) -> None:
    """Rotation and compress tokens are validated."""
    with pytest.raises(BinderyValidationError, match="rotate"):
        JobConfig(source_dir=tmp_path, output_path=tmp_path / "o.pdf", rotate=45)
    with pytest.raises(BinderyValidationError, match="compress"):
        JobConfig(source_dir=tmp_path, output_path=tmp_path / "o.pdf", compress="png")
    with pytest.raises(BinderyValidationError, match="jpeg_quality"):
        JobConfig(
            source_dir=tmp_path,
            output_path=tmp_path / "o.pdf",
            compress="jpeg",
            jpeg_quality=100,
        )


def test_transform_crop_and_rotate(tmp_path: Path) -> None:
    """Crop then rotate changes page geometry as expected."""
    page_path = _write_png(tmp_path / "p.png", (50, 30), (10, 20, 30))
    work = tmp_path / "work"
    work.mkdir()
    cfg = JobConfig(
        source_dir=tmp_path,
        output_path=tmp_path / "o.pdf",
        crop=CropBox(0, 0, 40, 20),
        rotate=90,
        margins=MarginSpec.uniform(0),
    )
    out = transform_page(PageFile(path=page_path, index=0), cfg, work)
    with Image.open(out) as image:
        assert image.size == (20, 40)


def test_transform_page_size_letterbox(tmp_path: Path) -> None:
    """Fixed page size produces exact pixel canvas at dpi."""
    page_path = _write_png(tmp_path / "p.png", (20, 20), (5, 5, 5))
    work = tmp_path / "work"
    work.mkdir()
    cfg = JobConfig(
        source_dir=tmp_path,
        output_path=tmp_path / "o.pdf",
        page_size="72x144",
        dpi=72,
        margins=MarginSpec.uniform(0),
    )
    out = transform_page(PageFile(path=page_path, index=0), cfg, work)
    with Image.open(out) as image:
        assert image.size == (72, 144)


def test_transform_jpeg_compress(tmp_path: Path) -> None:
    """jpeg profile writes a JPEG page file."""
    page_path = _write_png(tmp_path / "p.png", (30, 30), (1, 2, 3))
    work = tmp_path / "work"
    work.mkdir()
    cfg = JobConfig(
        source_dir=tmp_path,
        output_path=tmp_path / "o.pdf",
        compress="jpeg",
        jpeg_quality=70,
    )
    out = transform_page(PageFile(path=page_path, index=0), cfg, work)
    assert out.suffix.lower() in {".jpg", ".jpeg"}


def test_select_pages_order_and_reindex(tmp_path: Path) -> None:
    """Explicit page_names reorder pages and reindex stamps."""
    source = _pages(tmp_path)
    discovered = [
        PageFile(path=source / "page_1.png", index=0),
        PageFile(path=source / "page_2.png", index=1),
        PageFile(path=source / "page_10.png", index=2),
    ]
    selected = select_pages(discovered, ("page_10.png", "page_1.png"))
    assert [p.name for p in selected] == ["page_10.png", "page_1.png"]
    assert [p.index for p in selected] == [0, 1]


def test_select_pages_missing_name(tmp_path: Path) -> None:
    """Missing explicit page name is a validation error."""
    source = _pages(tmp_path)
    discovered = [PageFile(path=source / "page_1.png", index=0)]
    with pytest.raises(BinderyValidationError, match="page not found"):
        select_pages(discovered, ("nope.png",))


def test_run_job_respects_page_names(tmp_path: Path) -> None:
    """Assemble uses only the requested names in order."""
    source = _pages(tmp_path)
    out = tmp_path / "book.pdf"
    report = run_job(
        JobConfig(
            source_dir=source,
            output_path=out,
            page_names=("page_2.png", "page_1.png"),
        )
    )
    assert report.page_count == 2
    assert [p.name for p in report.pages] == ["page_2.png", "page_1.png"]
    assert len(PdfReader(out).pages) == 2


def test_run_job_a4_mediabox(tmp_path: Path) -> None:
    """page_size=a4 produces A4-ish mediabox in points."""
    source = tmp_path / "pages"
    _write_png(source / "p1.png", (100, 100), (12, 34, 56))
    out = tmp_path / "a4.pdf"
    run_job(JobConfig(source_dir=source, output_path=out, page_size="a4", dpi=72))
    page = PdfReader(out).pages[0]
    box = page.mediabox
    assert float(box.width) == pytest.approx(595.276, rel=0.02)
    assert float(box.height) == pytest.approx(841.89, rel=0.02)


def test_cli_build_with_workbench_flags(tmp_path: Path, capsys) -> None:
    """CLI accepts crop/rotate/page-size/compress/pages."""
    source = _pages(tmp_path)
    out = tmp_path / "book.pdf"
    code = main(
        [
            "build",
            str(source),
            "-o",
            str(out),
            "--pages",
            "page_1.png,page_2.png",
            "--rotate",
            "90",
            "--page-size",
            "letter",
            "--compress",
            "jpeg",
            "--jpeg-quality",
            "60",
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert out.is_file()
    assert "2 pages" in captured.out
    page = PdfReader(out).pages[0]
    assert float(page.mediabox.width) == pytest.approx(612.0, rel=0.02)


def test_cli_preview_writes_image(tmp_path: Path, capsys) -> None:
    """preview writes a transformed page image."""
    source = _pages(tmp_path)
    out = tmp_path / "preview.png"
    code = main(
        [
            "preview",
            str(source),
            "-o",
            str(out),
            "--page",
            "2",
            "--grayscale",
            "--rotate",
            "180",
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    written = list(tmp_path.glob("preview.*"))
    assert written
    assert "preview" in captured.out
    with Image.open(written[0]) as image:
        assert image.size[0] > 0


def test_cli_exclude_pages(tmp_path: Path, capsys) -> None:
    """--exclude drops named pages from the job."""
    source = _pages(tmp_path)
    out = tmp_path / "book.pdf"
    code = main(["build", str(source), "-o", str(out), "--exclude", "page_10.png"])
    captured = capsys.readouterr()
    assert code == 0
    assert "2 pages" in captured.out


def test_cli_help_lists_preview(capsys) -> None:
    """Help documents the preview verb."""
    assert main(["--help"]) == 0
    assert "bindery preview" in capsys.readouterr().out


def test_gui_smoke_still_imports() -> None:
    """GUI module remains importable."""
    from bindery.gui import BinderyApp

    assert callable(BinderyApp)
