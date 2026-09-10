"""Domain models (pure value objects, no I/O)."""

from __future__ import annotations

from bindery.models.config import JobConfig
from bindery.models.crop import CropBox, MarginSpec
from bindery.models.page import PageFile

__all__ = [
    "CropBox",
    "JobConfig",
    "MarginSpec",
    "PageFile",
]
