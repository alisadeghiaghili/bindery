"""Tests for job files, multi-source chapters, dry-run, and bookmarks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader

from bindery.cli import main
from bindery.exceptions import BinderyValidationError
from bindery.models.config import JobConfig
from bindery.models.job_config_file import job_config_from_file
from bindery.models.jobfile import SourceSpec, load_job_file
from bindery.orchestration.pipeline import discover_job_pages, run_job


def _png(path: Path, color: tuple[int, int, int]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (20, 30), color).save(path)
    return path


def _book(tmp_path: Path) -> tuple[Path, Path]:
    ch1 = tmp_path / "ch1"
    ch2 = tmp_path / "ch2"
    _png(ch1 / "a.png", (200, 0, 0))
    _png(ch1 / "b.png", (0, 200, 0))
    _png(ch2 / "c.png", (0, 0, 200))
    _png(ch2 / "skip.png", (1, 1, 1))
    return ch1, ch2


def test_load_job_file_toml(tmp_path: Path) -> None:
    """TOML job files parse into normalized options."""
    ch1, ch2 = _book(tmp_path)
    job = tmp_path / "book.toml"
    job.write_text(
        f"""
output = "out/book.pdf"
title = "Chapters"
dpi = 72
margin = 2
stamp = true
bookmarks = "chapters"
compress = "jpeg"
jpeg_quality = 70
sources = [
  "{ch1.as_posix()}",
  {{ path = "{ch2.as_posix()}", exclude = ["skip.png"] }},
]
""",
        encoding="utf-8",
    )
    data = load_job_file(job)
    assert data["output"] == "out/book.pdf"
    assert data["title"] == "Chapters"
    assert data["bookmark_mode"] == "chapters"
    assert data["compress"] == "jpeg"
    assert len(data["sources"]) == 2
    assert data["sources"][1].exclude == ("skip.png",)


def test_load_job_file_json_unknown_key(tmp_path: Path) -> None:
    """Unknown job-file keys are rejected."""
    job = tmp_path / "bad.json"
    job.write_text(
        json.dumps({"output": "o.pdf", "sources": ["pages"], "nope": 1}),
        encoding="utf-8",
    )
    with pytest.raises(BinderyValidationError, match="unknown keys"):
        load_job_file(job)


def test_job_config_multi_source_and_excludes(tmp_path: Path) -> None:
    """Job file multi-source discovers both chapters and drops excludes."""
    ch1, ch2 = _book(tmp_path)
    job = tmp_path / "book.json"
    job.write_text(
        json.dumps(
            {
                "output": "book.pdf",
                "bookmarks": "chapters",
                "sources": [
                    str(ch1),
                    {"path": str(ch2), "exclude": ["skip.png"]},
                ],
            }
        ),
        encoding="utf-8",
    )
    config = job_config_from_file(job)
    pages, starts, labels = discover_job_pages(config)
    assert [p.name for p in pages] == ["a.png", "b.png", "c.png"]
    assert starts == [0, 2]
    assert labels == ["ch1", "ch2"]
    assert config.bookmark_mode == "chapters"


def test_run_job_multi_source_bookmarks(tmp_path: Path) -> None:
    """Assembled multi-source PDF has outline items for chapters."""
    ch1, ch2 = _book(tmp_path)
    out = tmp_path / "book.pdf"
    config = JobConfig(
        source_dir=ch1,
        output_path=out,
        extra_sources=(ch2,),
        sources=(
            SourceSpec(path=ch1),
            SourceSpec(path=ch2, exclude=("skip.png",)),
        ),
        bookmark_mode="chapters",
        dpi=72,
    )
    report = run_job(config)
    assert report.page_count == 3
    reader = PdfReader(out)
    assert len(reader.pages) == 3
    outline = reader.outline
    assert outline, "expected PDF outline entries"


def test_run_job_bookmarks_filenames(tmp_path: Path) -> None:
    """filenames mode still writes a PDF with outline support."""
    ch1, _ = _book(tmp_path)
    out = tmp_path / "one.pdf"
    run_job(
        JobConfig(
            source_dir=ch1,
            output_path=out,
            bookmark_mode="filenames",
            dpi=72,
        )
    )
    reader = PdfReader(out)
    assert len(reader.pages) == 2
    assert reader.outline


def test_cli_job_dry_run_and_run(tmp_path: Path, capsys) -> None:
    """bindery job --dry-run lists pages; job without dry-run writes PDF."""
    ch1, ch2 = _book(tmp_path)
    job = tmp_path / "book.toml"
    job.write_text(
        f"""
output = "{(tmp_path / "out.pdf").as_posix()}"
bookmarks = "chapters"
sources = [
  "{ch1.as_posix()}",
  {{ path = "{ch2.as_posix()}", exclude = ["skip.png"] }},
]
""",
        encoding="utf-8",
    )
    code = main(["job", str(job), "--dry-run"])
    captured = capsys.readouterr()
    assert code == 0
    assert "pages: 3" in captured.out
    assert "chapter" in captured.out.lower()
    assert not (tmp_path / "out.pdf").exists()

    code = main(["job", str(job)])
    captured = capsys.readouterr()
    assert code == 0
    assert "Wrote" in captured.out
    assert (tmp_path / "out.pdf").is_file()


def test_cli_build_extra_source_and_bookmarks(tmp_path: Path, capsys) -> None:
    """build --extra-source and --bookmarks assemble chapters."""
    ch1, ch2 = _book(tmp_path)
    out = tmp_path / "book.pdf"
    code = main(
        [
            "build",
            str(ch1),
            "-o",
            str(out),
            "--extra-source",
            str(ch2),
            "--exclude",
            "skip.png",
            "--bookmarks",
            "filenames",
        ]
    )
    captured = capsys.readouterr()
    assert code == 0, captured.err
    assert "Wrote" in captured.out
    assert len(PdfReader(out).pages) == 3


def test_cli_job_missing_file(tmp_path: Path, capsys) -> None:
    """Missing job file is an I/O error."""
    code = main(["job", str(tmp_path / "nope.toml")])
    assert code == 4
    assert "not found" in capsys.readouterr().err.lower()


def test_cli_help_lists_job(capsys) -> None:
    """Help documents the job verb."""
    assert main(["--help"]) == 0
    assert "bindery job" in capsys.readouterr().out


def test_job_config_rejects_bad_bookmark_mode(tmp_path: Path) -> None:
    """bookmark_mode is validated on JobConfig."""
    with pytest.raises(BinderyValidationError, match="bookmark"):
        JobConfig(
            source_dir=tmp_path / "pages",
            output_path=tmp_path / "o.pdf",
            bookmark_mode="outline",
        )
