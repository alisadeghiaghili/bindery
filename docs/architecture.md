# Architecture

## Layering

```text
interface  →  orchestration  →  domain  ←  adapters
                 │                ↑
                 └──── models ────┘
```

Dependencies point inward only. `models` is a shared value-object layer: domain and adapters both may import it; orchestration may import domain, adapters, and models.

| Layer | Responsibility | May import |
|---|---|---|
| `interface` | CLI / GUI, argument parsing, human-facing errors | orchestration, models, exceptions |
| `orchestration` | pipeline steps, progress, resume | domain, adapters, models, exceptions |
| `domain` | pure geometry, ordering, validation | models, exceptions |
| `adapters` | filesystem, Pillow, PDF writers | models, domain, exceptions |
| `models` | immutable config/page types | stdlib only + exceptions |

Adapters may depend on domain pure helpers (for example natural ordering used during filesystem discovery). Domain must never import adapters or orchestration.

## v0.7.0 status

Present:

- models, domain, adapters, orchestration (progress + content-aware resume)
- Resume fingerprint: options + page identity (name/size/mtime) + title/author + resolved source/output paths
- CLI: `build` (argparse), `inspect`, `doctor`, `gui`
- PDF metadata via `--title` / `--author` (and GUI fields)
- tkinter GUI shell over `run_job` (lazy Tcl/Tk import; no UI business logic)
- Stamp footer band so page numbers do not overlay content
- Windows `bindery.exe` on Releases
- CI: Ubuntu + Windows × Python 3.12 + 3.13

Still missing: OCR extra, PySide6 upgrade path (optional).

## Non-goals (permanent)

- No scraping or remote content fetch.
- No DRM circumvention.
- No mandatory cloud services.
