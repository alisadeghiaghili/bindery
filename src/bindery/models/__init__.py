"""Domain models (pure value objects, no I/O)."""

from __future__ import annotations

from bindery.models.config import JobConfig
from bindery.models.crop import CropBox, MarginSpec
from bindery.models.page import PageFile
from bindery.models.page_size import PAGE_PRESETS, parse_page_size

__all__ = [
    "PAGE_PRESETS",
    "CropBox",
    "JobConfig",
    "MarginSpec",
    "PageFile",
    "parse_page_size",
]
