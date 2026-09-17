# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- CLI `--title` / `--author` and GUI Title/Author fields write PDF document metadata.
- `JobConfig.title` / `JobConfig.author` (blank strings normalize to `None`).
- Resume fingerprint includes title, author, resolved `source_dir`, and resolved `output_path`.
- Stamp jobs reserve a footer band when bottom margin is thinner than `_STAMP_FOOTER_BAND` so numbers do not overlay page content.
- Automated GUI cancel-control tests (flag set, UI reset on cancel/error).

### Fixed

- Resume fingerprint now includes page size and mtime, so rewriting an image under the same filename rebuilds the PDF.
- `--grayscale` / `JobConfig.grayscale` keeps intermediate pages as mode `L` instead of converting back to RGB.
- Natural sort is total: `page_02.png` vs `page_2.png` no longer depend on directory iteration order.
- `JobConfig` and `ensure_source_output_distinct` compare resolved paths (`pages` vs `./pages`).
- Transform workdir uses an isolated system temp directory instead of a predictable path next to the output PDF.
- `bindery doctor` reports `sys.platform` instead of `platform.platform()`, which can fatal-crash on Windows WMI probes.
- PyInstaller spec no longer lists undeclared `pikepdf` as a hidden import.
- `tools/doc_audit.py` documentation no longer references missing `ENGINEERING-STANDARDS.md` / `claim_audit.py`.

### Changed

- Package root exports `JobConfig`, `JobReport`, and `run_job`.
- CI quality gates run on Ubuntu and Windows, Python 3.12 and 3.13.
- Coverage policy: `fail_under=90` measures package surface excluding `gui.py` (tkinter shell; smoke-tested when Tcl/Tk loads).
- `write_pdf` docstring matches implementation (img2pdf metadata kwargs; pypdf is validation-only).
- Architecture doc allows adapters → domain and no longer describes a nonexistent models edge in the old diagram.
- Removed empty `ocr` optional extra; `gui` extra remains reserved for a future PySide6 shell.

## [0.6.0] - 2026-09-10

### Added

- Desktop GUI (`bindery gui`) using tkinter, stdlib only.
- GUI calls the same `run_job` pipeline; worker thread + progress queue.
- Cooperative cancel, progress bar, log panel, margin/dpi/options form.
- Optional extra `bindery[gui]` reserved for future PySide6; current GUI needs no extra install.

### Notes

- PySide6 was evaluated but not adopted for v0.6: multi-hundred-MB wheels are unnecessary for this form. tkinter keeps the GUI dependency-free.

## [0.5.0] - 2026-09-10

### Added

- `bindery inspect SOURCE`: list pages in assemble order with pixel sizes.
- `bindery doctor`: report Python, bindery, Pillow, img2pdf, pypdf health.
- Usage text covers all commands.

## [0.4.0] - 2026-09-10

### Added

- Progress events (`ProgressEvent`, `ProgressCallback`) emitted from the pipeline.
- CLI progress lines on stderr during transform/assemble.
- Resume manifest sidecar (`*.pdf.bindery.json`) with config fingerprint.
- Idempotent rebuild: identical job skips and prints `Up to date`.
- `--force` / `JobConfig.force` to rebuild when needed.
- Structured timing log after a successful write.

## [0.3.1] - 2026-09-10

### Fixed

- PDF page geometry now honors `--dpi` / `JobConfig.dpi` via an img2pdf `layout_fun`.
- Previously img2pdf 0.6.x silently ignored the convert `dpi` kwarg and always used 96.
- Pages smaller than 3pt after dpi conversion are scaled up so viewers accept them.

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

[Unreleased]: https://github.com/alisadeghiaghili/bindery/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/alisadeghiaghili/bindery/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/alisadeghiaghili/bindery/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/alisadeghiaghili/bindery/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/alisadeghiaghili/bindery/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/alisadeghiaghili/bindery/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/alisadeghiaghili/bindery/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/alisadeghiaghili/bindery/releases/tag/v0.1.0
