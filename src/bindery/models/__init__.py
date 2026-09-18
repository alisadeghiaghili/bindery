"""Domain models (pure value objects and job-file helpers)."""

from __future__ import annotations

from bindery.models.config import JobConfig
from bindery.models.crop import CropBox, MarginSpec
from bindery.models.job_config_file import job_config_from_file, job_config_from_mapping
from bindery.models.jobfile import SourceSpec, load_job_file
from bindery.models.page import PageFile
from bindery.models.page_size import PAGE_PRESETS, parse_page_size

__all__ = [
    "PAGE_PRESETS",
    "CropBox",
    "JobConfig",
    "MarginSpec",
    "PageFile",
    "SourceSpec",
    "job_config_from_file",
    "job_config_from_mapping",
    "load_job_file",
    "parse_page_size",
]
