"""Domain package: pure geometry, ordering, and validation."""

from __future__ import annotations

from bindery.domain.geometry import (
    compute_output_size,
    expand_box_by_margins,
    is_valid_crop,
    normalize_margins,
    pad_image_size,
)
from bindery.domain.ordering import natural_sort_key, sort_page_names
from bindery.domain.validate import ensure_positive_size, ensure_source_output_distinct

__all__ = [
    "compute_output_size",
    "ensure_positive_size",
    "ensure_source_output_distinct",
    "expand_box_by_margins",
    "is_valid_crop",
    "natural_sort_key",
    "normalize_margins",
    "pad_image_size",
    "sort_page_names",
]
