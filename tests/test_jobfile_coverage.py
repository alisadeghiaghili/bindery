"""Extra coverage for job-file errors, bookmark titles, and CLI job paths."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader

from bindery.adapters.bookmarks import apply_bookmarks, bookmark_titles
from bindery.cli import main
from bindery.exceptions import BinderyValidationError
from bindery.models.config import JobConfig
from bindery.models.job_config_file import job_config_from_file
from bindery.models.jobfile import SourceSpec, load_job_file


def _png(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (16, 16), (9, 9, 9)).save(path)
    return path


def test_bookmark_titles_modes() -> None:
    """none/filenames/chapters produce expected title lists."""
    assert bookmark_titles("none", ["a.png", "b.png"], [0], ["ch1"]) is None
    assert bookmark_titles("filenames", ["a.png", "b.png"], [], []) == ["a.png", "b.png"]
    titles = bookmark_titles("chapters", ["a.png", "b.png", "c.png"], [0, 2], ["ch1", "ch2"])
    assert titles == ["ch1", "ch1", "ch2"]


def test_bookmark_titles_invalid_mode() -> None:
    """Unknown bookmark modes raise."""
    with pytest.raises(BinderyValidationError, match="bookmark"):
        bookmark_titles("outline", ["a.png"], [], [])


def test_apply_bookmarks_roundtrip(tmp_path: Path) -> None:
    """apply_bookmarks writes outline items onto an existing PDF."""
    src = tmp_path / "p.png"
    _png(src)
    out = tmp_path / "doc.pdf"
    from bindery.adapters.pdf import write_pdf

    write_pdf([src, src], out)
    apply_bookmarks(out, ["One", "Two"])
    outline = PdfReader(out).outline
    assert outline


def test_apply_bookmarks_count_mismatch(tmp_path: Path) -> None:
    """Title count must match page count."""
    src = tmp_path / "p.png"
    _png(src)
    out = tmp_path / "doc.pdf"
    from bindery.adapters.pdf import write_pdf

    write_pdf([src], out)
    with pytest.raises(BinderyValidationError, match="bookmark count"):
        apply_bookmarks(out, ["a", "b"])


def test_job_file_requires_output_and_sources(tmp_path: Path) -> None:
    """Job files must declare output and sources."""
    job = tmp_path / "j.json"
    job.write_text(json.dumps({"sources": ["pages"]}), encoding="utf-8")
    with pytest.raises(BinderyValidationError, match="output"):
        load_job_file(job)
    job.write_text(json.dumps({"output": "o.pdf", "sources": []}), encoding="utf-8")
    with pytest.raises(BinderyValidationError, match="sources"):
        load_job_file(job)


def test_job_file_bad_source_entry(tmp_path: Path) -> None:
    """Source entries need a path key."""
    job = tmp_path / "j.json"
    job.write_text(
        json.dumps({"output": "o.pdf", "sources": [{"pages": ["a.png"]}]}),
        encoding="utf-8",
    )
    with pytest.raises(BinderyValidationError, match="requires path"):
        load_job_file(job)


def test_job_file_bad_extension(tmp_path: Path) -> None:
    """Unsupported job file extensions are rejected."""
    job = tmp_path / "j.txt"
    job.write_text("{}", encoding="utf-8")
    with pytest.raises(BinderyValidationError, match=r"toml or \.json"):
        load_job_file(job)


def test_job_file_bad_bookmarks(tmp_path: Path) -> None:
    """Invalid bookmark mode in job file fails."""
    job = tmp_path / "j.json"
    job.write_text(
        json.dumps({"output": "o.pdf", "sources": ["pages"], "bookmarks": "toc"}),
        encoding="utf-8",
    )
    with pytest.raises(BinderyValidationError, match="bookmarks"):
        load_job_file(job)


def test_source_spec_duplicate_pages(tmp_path: Path) -> None:
    """SourceSpec rejects duplicate page names."""
    with pytest.raises(BinderyValidationError, match="duplicates"):
        SourceSpec(path=tmp_path, page_names=("a.png", "a.png"))


def test_cli_job_unknown_option(capsys) -> None:
    """Unknown job flags are usage errors."""
    assert main(["job", "x.toml", "--nope"]) == 2
    assert "unknown" in capsys.readouterr().err.lower()


def test_cli_job_requires_file(capsys) -> None:
    """job without JOBFILE is a usage error."""
    assert main(["job"]) == 2
    assert "JOBFILE" in capsys.readouterr().err


def test_cli_job_two_files(capsys) -> None:
    """job accepts only one JOBFILE."""
    assert main(["job", "a.toml", "b.toml"]) == 2
    assert "single" in capsys.readouterr().err.lower()


def test_cli_build_extra_source_validation_error(tmp_path: Path, capsys) -> None:
    """Missing extra source directory maps to I/O error 4."""
    src = tmp_path / "pages"
    _png(src / "a.png")
    code = main(
        [
            "build",
            str(src),
            "-o",
            str(tmp_path / "o.pdf"),
            "--extra-source",
            str(tmp_path / "missing"),
        ]
    )
    assert code in {3, 4}
    assert capsys.readouterr().err


def test_job_config_from_file_relative_paths(tmp_path: Path) -> None:
    """Relative job-file paths resolve against the job file directory."""
    (tmp_path / "pages").mkdir()
    _png(tmp_path / "pages" / "a.png")
    job = tmp_path / "job.toml"
    job.write_text(
        """
output = "out.pdf"
sources = ["pages"]
bookmarks = "filenames"
""",
        encoding="utf-8",
    )
    cfg = job_config_from_file(job)
    assert (
        cfg.output_path == (tmp_path / "out.pdf").resolve()
        or cfg.output_path == tmp_path / "out.pdf"
    )
    assert cfg.source_dir.name == "pages"
    assert cfg.bookmark_mode == "filenames"


def test_job_config_duplicate_page_names(tmp_path: Path) -> None:
    """JobConfig rejects duplicate explicit page_names."""
    with pytest.raises(BinderyValidationError, match="duplicates"):
        JobConfig(
            source_dir=tmp_path / "p",
            output_path=tmp_path / "o.pdf",
            page_names=("a.png", "a.png"),
        )


def test_preview_page_out_of_range(tmp_path: Path, capsys) -> None:
    """preview --page outside range is validation error."""
    src = tmp_path / "pages"
    _png(src / "a.png")
    code = main(["preview", str(src), "-o", str(tmp_path / "p.png"), "--page", "5"])
    assert code == 3
    assert "page" in capsys.readouterr().err.lower()
