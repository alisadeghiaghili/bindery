"""Tests for inspect and doctor CLI commands."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from bindery.cli import main


def _make_pages(tmp_path: Path) -> Path:
    source = tmp_path / "pages"
    source.mkdir()
    for name, color in (
        ("page_2.png", (200, 0, 0)),
        ("page_10.png", (0, 200, 0)),
        ("page_1.png", (0, 0, 200)),
    ):
        Image.new("RGB", (40, 60), color).save(source / name)
    (source / "readme.txt").write_text("skip", encoding="utf-8")
    return source


def test_inspect_reports_order_and_count(tmp_path: Path, capsys) -> None:
    """inspect lists pages in natural order with a count line."""
    source = _make_pages(tmp_path)
    code = main(["inspect", str(source)])
    out = capsys.readouterr().out
    assert code == 0
    assert "page_1.png" in out
    assert "page_10.png" in out
    assert out.index("page_1.png") < out.index("page_2.png") < out.index("page_10.png")
    assert "3" in out
    assert "readme.txt" not in out


def test_inspect_missing_dir(tmp_path: Path, capsys) -> None:
    """Missing directory is an I/O error (exit 4)."""
    code = main(["inspect", str(tmp_path / "nope")])
    captured = capsys.readouterr()
    assert code == 4
    assert "does not exist" in captured.err


def test_inspect_empty_dir(tmp_path: Path, capsys) -> None:
    """Empty directory is a validation error (exit 3)."""
    empty = tmp_path / "empty"
    empty.mkdir()
    code = main(["inspect", str(empty)])
    captured = capsys.readouterr()
    assert code == 3
    assert "no page" in captured.err


def test_doctor_reports_environment(capsys) -> None:
    """doctor exits 0 and prints package/versions."""
    code = main(["doctor"])
    out = capsys.readouterr().out
    assert code == 0
    assert "python" in out.lower()
    assert "pillow" in out.lower()
    assert "img2pdf" in out.lower()
    assert "pypdf" in out.lower()
    assert "bindery" in out.lower()


def test_inspect_requires_source(capsys) -> None:
    """inspect without a path is usage error."""
    code = main(["inspect"])
    captured = capsys.readouterr()
    assert code == 2
    assert "SOURCE" in captured.err or "requires" in captured.err
