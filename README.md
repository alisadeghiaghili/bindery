# bindery

Assemble image folders into a single, clean PDF document.

**Status:** v0.8.0 — CLI + desktop GUI on the same pipeline. Windows `bindery.exe` is published on Releases.

## What this is

`bindery` takes a directory of page images (PNG/JPEG/WebP/TIFF/BMP) and produces one multi-page PDF, with optional margins, grayscale, page stamps, and title metadata. Processing is local.

## Non-goals

These are permanent product boundaries, not backlog:

- **No scraping.** bindery does not fetch content from websites, ebook platforms, or any remote service. Inputs must be files you already have the right to use.
- **No DRM circumvention.** It will not open protected commercial ebook formats or bypass access controls.
- **No cloud dependency.** All processing is local.

If a workflow needs the above, it belongs in a different product.

## Install

### Standalone Windows executable

Download `bindery.exe` from [Releases](https://github.com/alisadeghiaghili/bindery/releases) (asset is versioned as `bindery-<version>-windows-x64.exe`).

### From source

```bash
bindery build ./pages -o book.pdf --margin 8 --grayscale --stamp --dpi 300
bindery build ./pages -o book.pdf --title "My Book" --author "Name"
bindery build ./pages -o book.pdf --crop 0,0,1200,1800 --rotate 90 --page-size a4
bindery build ./pages -o book.pdf --compress jpeg --jpeg-quality 80
bindery build ./pages -o book.pdf --pages page_2.png,page_1.png
bindery build ./pages -o book.pdf --exclude cover.png --force
bindery preview ./pages -o preview.png --page 1 --grayscale
bindery job book.toml --dry-run
bindery job book.toml
bindery build ./ch1 -o book.pdf --extra-source ./ch2 --bookmarks chapters
bindery inspect ./pages
bindery doctor
bindery gui
bindery --version
bindery --help
```

Requires Python 3.12+.

## Usage

```bash
bindery build ./pages -o book.pdf --margin 8 --grayscale --stamp --dpi 300
bindery build ./pages -o book.pdf --title "My Book" --author "Name"
bindery build ./pages -o book.pdf --force   # rebuild even if up to date
bindery inspect ./pages
bindery doctor
bindery gui
bindery --version
bindery --help
```

A sidecar `book.pdf.bindery.json` records a config fingerprint (options + page identity + metadata). Re-running an identical job prints `Up to date` and skips work unless you pass `--force`.

Exit codes: `0` success, `2` usage, `3` validation, `4` I/O.

GUI includes page reorder/exclude and a first-page preview thumbnail.

## Development

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv run pytest
uv run python tools/doc_audit.py --path src/bindery --style google --require-example
```

Build the Windows executable locally:

```bash
uv run pyinstaller --clean --noconfirm bindery.spec
dist\bindery.exe --version
```

## License

Apache License 2.0. See [LICENSE](LICENSE).

## Author

Ali Sadeghi Aghili
