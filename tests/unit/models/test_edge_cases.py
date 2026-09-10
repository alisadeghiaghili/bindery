"""Extra coverage for edge-case branches in models."""

from __future__ import annotations

from pathlib import Path

import pytest

from bindery.exceptions import BinderyValidationError
from bindery.models.config import JobConfig
from bindery.models.crop import CropBox, MarginSpec
from bindery.models.page import PageFile


def test_margin_rejects_bool() -> None:
    """Booleans are not valid pixel counts."""
    with pytest.raises(BinderyValidationError, match="must be an int"):
        MarginSpec(left=True)  # type: ignore[arg-type]


def test_margin_rejects_float() -> None:
    """Floats are rejected even if whole numbers."""
    with pytest.raises(BinderyValidationError, match="must be an int"):
        MarginSpec.uniform(1.0)  # type: ignore[arg-type]


def test_crop_rejects_non_int_right() -> None:
    """Crop edges must be ints."""
    with pytest.raises(BinderyValidationError, match="crop right"):
        CropBox(left=0, top=0, right="10", bottom=10)  # type: ignore[arg-type]


def test_crop_as_pil_box() -> None:
    """PIL box order is left, top, right, bottom."""
    box = CropBox(1, 2, 3, 4)
    assert box.as_pil_box() == (1, 2, 3, 4)


def test_page_file_coerces_str_path(tmp_path: Path) -> None:
    """String paths are coerced to ``Path``."""
    page = PageFile(path=tmp_path / "a.png", index=0)  # type: ignore[arg-type]
    assert isinstance(page.path, Path)


def test_page_file_rejects_bool_index(tmp_path: Path) -> None:
    """Booleans are not valid indices."""
    with pytest.raises(BinderyValidationError, match="index"):
        PageFile(path=tmp_path / "a.png", index=True)  # type: ignore[arg-type]


def test_job_config_rejects_bool_dpi(tmp_path: Path) -> None:
    """Booleans are not valid dpi values."""
    with pytest.raises(BinderyValidationError, match="dpi"):
        JobConfig(source_dir=tmp_path, output_path=tmp_path / "o.pdf", dpi=True)  # type: ignore[arg-type]


def test_job_config_coerces_str_paths(tmp_path: Path) -> None:
    """String paths are coerced to ``Path``."""
    cfg = JobConfig(source_dir=str(tmp_path / "pages"), output_path=str(tmp_path / "b.pdf"))  # type: ignore[arg-type]
    assert isinstance(cfg.source_dir, Path)
    assert isinstance(cfg.output_path, Path)
