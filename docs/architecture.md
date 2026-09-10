# Architecture

## Layering

```text
interface  →  orchestration  →  domain  ←  adapters  ←  models
```

Dependencies point inward only.

| Layer | Responsibility | May import |
|---|---|---|
| `interface` | CLI / GUI, argument parsing, human-facing errors | orchestration, models, exceptions |
| `orchestration` | pipeline steps, progress, resume | domain, adapters, models, exceptions |
| `domain` | pure geometry, ordering, validation | models, exceptions |
| `adapters` | filesystem, Pillow, PDF writers | models, exceptions |
| `models` | immutable config/page types | stdlib only |

## v0.6.0 status

Present:

- models, domain, adapters, orchestration (progress + resume)
- CLI: `build`, `inspect`, `doctor`, `gui`
- tkinter GUI shell over `run_job` (no UI business logic)
- Windows `bindery.exe` on Releases

Still missing: OCR extra, PySide6 upgrade path (optional).

## Non-goals (permanent)

- No scraping or remote content fetch.
- No DRM circumvention.
- No mandatory cloud services.
