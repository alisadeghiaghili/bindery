"""Adapters: filesystem, Pillow images, PDF writers."""

from __future__ import annotations

from bindery.adapters.fs import IMAGE_SUFFIXES, discover_page_files, list_image_paths
from bindery.adapters.images import (
    load_image,
    pad_to_canvas,
    stamp_page_number,
    to_grayscale,
)
from bindery.adapters.pdf import write_pdf

__all__ = [
    "IMAGE_SUFFIXES",
    "discover_page_files",
    "list_image_paths",
    "load_image",
    "pad_to_canvas",
    "stamp_page_number",
    "to_grayscale",
    "write_pdf",
]
