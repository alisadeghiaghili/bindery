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

## v0.3.0 status

Present:

- models, domain, adapters (fs/images/pdf), orchestration pipeline
- CLI `build` + Windows `bindery.exe` release asset
- single-pass PDF write (no per-page rewrite)

Still missing: GUI, OCR extra, resume/manifest, rich progress UI.

## Non-goals (permanent)

- No scraping or remote content fetch.
- No DRM circumvention.
- No mandatory cloud services.
