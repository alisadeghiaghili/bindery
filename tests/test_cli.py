"""CLI tests including build."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image

from bindery import get_version
from bindery.cli import main


def test_no_args_prints_version(capsys: pytest.CaptureFixture[str]) -> None:
    """Default invocation reports the package version."""
    code = main([])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == f"bindery {get_version()}"


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    """``--version`` prints the same string as the default path."""
    code = main(["--version"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == f"bindery {get_version()}"


def test_short_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    """``-V`` is an alias for ``--version``."""
    code = main(["-V"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == f"bindery {get_version()}"


def test_help_flag(capsys: pytest.CaptureFixture[str]) -> None:
    """``--help`` exits zero and documents build."""
    code = main(["--help"])
    captured = capsys.readouterr()
    assert code == 0
    assert "bindery build" in captured.out


def test_short_help_flag(capsys: pytest.CaptureFixture[str]) -> None:
    """``-h`` is an alias for ``--help``."""
    code = main(["-h"])
    captured = capsys.readouterr()
    assert code == 0
    assert "Usage:" in captured.out


def test_unknown_args_exit_2(capsys: pytest.CaptureFixture[str]) -> None:
    """Unknown flags are a usage error."""
    code = main(["--nope"])
    captured = capsys.readouterr()
    assert code == 2
    assert "unknown arguments" in captured.err


def test_uses_sys_argv_when_argv_is_none(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``argv=None`` reads the real process argv (minus program name)."""
    monkeypatch.setattr(sys, "argv", ["bindery", "--version"])
    code = main(None)
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == f"bindery {get_version()}"


def test_build_requires_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """build without -o is a usage error."""
    source = tmp_path / "pages"
    source.mkdir()
    Image.new("RGB", (8, 8)).save(source / "a.png")
    code = main(["build", str(source)])
    captured = capsys.readouterr()
    assert code == 2
    assert "--output" in captured.err


def test_build_end_to_end(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """build writes a PDF from a folder of images."""
    source = tmp_path / "pages"
    source.mkdir()
    Image.new("RGB", (16, 16), (20, 30, 40)).save(source / "p1.png")
    Image.new("RGB", (16, 16), (40, 30, 20)).save(source / "p2.png")
    output = tmp_path / "book.pdf"
    code = main(
        [
            "build",
            str(source),
            "-o",
            str(output),
            "--margin",
            "1",
            "--grayscale",
            "--stamp",
            "--dpi",
            "72",
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert output.is_file()
    assert "2 pages" in captured.out


def test_build_missing_source(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Missing source directory maps to I/O exit code 4."""
    code = main(["build", str(tmp_path / "nope"), "-o", str(tmp_path / "o.pdf")])
    captured = capsys.readouterr()
    assert code == 4
    assert "does not exist" in captured.err


def test_build_empty_source(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Empty source maps to validation exit code 3."""
    source = tmp_path / "empty"
    source.mkdir()
    code = main(["build", str(source), "-o", str(tmp_path / "o.pdf")])
    captured = capsys.readouterr()
    assert code == 3
    assert "no page" in captured.err
