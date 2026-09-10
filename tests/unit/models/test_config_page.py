"""Tests for page file and job configuration models."""

from __future__ import annotations

from pathlib import Path

import pytest

from bindery.exceptions import BinderyValidationError
from bindery.models.config import JobConfig
from bindery.models.crop import MarginSpec
from bindery.models.page import PageFile


def test_page_file_holds_path_and_index(tmp_path: Path) -> None:
    """A page record is an immutable (path, index) pair."""
    path = tmp_path / "page_1.png"
    page = PageFile(path=path, index=0)
    assert page.name == "page_1.png"
    assert page.index == 0


def test_page_file_rejects_negative_index(tmp_path: Path) -> None:
    """Page indices are zero-based and non-negative."""
    with pytest.raises(BinderyValidationError):
        PageFile(path=tmp_path / "a.png", index=-1)


def test_job_config_defaults(tmp_path: Path) -> None:
    """Source and output are required; optional knobs have safe defaults."""
    source = tmp_path / "pages"
    output = tmp_path / "book.pdf"
    config = JobConfig(source_dir=source, output_path=output)
    assert config.margins == MarginSpec()
    assert config.grayscale is False
    assert config.stamp_page_numbers is False
    assert config.dpi == 300


def test_job_config_rejects_bad_dpi(tmp_path: Path) -> None:
    """DPI must be a positive integer."""
    with pytest.raises(BinderyValidationError, match="dpi"):
        JobConfig(source_dir=tmp_path, output_path=tmp_path / "o.pdf", dpi=0)


def test_job_config_rejects_same_source_and_output_file(tmp_path: Path) -> None:
    """Output cannot overwrite an input path that equals source as a file."""
    page = tmp_path / "book.pdf"
    with pytest.raises(BinderyValidationError, match="output"):
        JobConfig(source_dir=page, output_path=page)


def test_job_config_allows_directory_source_and_file_output(tmp_path: Path) -> None:
    """Normal layout: directory of images in, single PDF out."""
    source = tmp_path / "pages"
    output = tmp_path / "out" / "book.pdf"
    config = JobConfig(source_dir=source, output_path=output, grayscale=True)
    assert config.grayscale is True
    assert config.source_dir == source
