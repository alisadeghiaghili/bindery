# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-09-10

### Added

- Adapters: image discovery (`fs`), Pillow transforms (`images`), PDF assembly (`pdf`).
- Orchestration: `assemble_job` / `run_job` with temp workspace cleanup.
- CLI: `bindery build SOURCE -o OUTPUT [--margin N] [--grayscale] [--stamp] [--dpi N]`.
- Exit codes: `0` ok, `2` usage, `3` validation, `4` I/O.
- Windows console executable `bindery.exe` (PyInstaller, attached to GitHub Releases).
- Integration tests for end-to-end assemble.

### Dependencies

- `pillow`, `img2pdf`, `pypdf` (runtime); `pyinstaller` (dev).

## [0.2.0] - 2026-09-10

### Added

- `bindery.models`: `MarginSpec`, `CropBox`, `PageFile`, `JobConfig` (frozen dataclasses).
- `bindery.domain.geometry`: `compute_output_size`, `pad_image_size`, `normalize_margins`, `is_valid_crop`, `expand_box_by_margins`.
- `bindery.domain.ordering`: `natural_sort_key`, `sort_page_names` for `page_2` < `page_10`.
- `bindery.domain.validate`: `ensure_positive_size`, `ensure_source_output_distinct`.
- Unit tests for domain and models (77 tests, coverage above 90%).

### Notes

- Domain remains pure: no filesystem or Pillow imports.
- Adapters and CLI `build` still land in later 0.x releases.

## [0.1.0] - 2026-09-10

### Added

- Initial package skeleton under `src/bindery`.
- Declared version `0.1.0` and `get_version()` helper.
- Exception hierarchy rooted at `BinderyError` (`BinderyConfigError`, `BinderyIOError`, `BinderyValidationError`).
- Minimal CLI: `bindery --version` / `bindery --help` (exit code `2` on unknown args).
- Development toolchain: ruff, mypy (strict), pytest.
- GitHub Actions CI workflow (lint, format, type, test, doc audit).
- Apache License 2.0.
- README with explicit non-goals (no scraping, no DRM circumvention).

[Unreleased]: https://github.com/alisadeghiaghili/bindery/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/alisadeghiaghili/bindery/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/alisadeghiaghili/bindery/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/alisadeghiaghili/bindery/releases/tag/v0.1.0
