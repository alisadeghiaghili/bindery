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

## v0.2.0 status

Present:

- package shell, exceptions, minimal CLI (`--version` / `--help`)
- `models`: `MarginSpec`, `CropBox`, `PageFile`, `JobConfig`
- `domain`: geometry, natural ordering, validation

Still missing: adapters (Pillow/PDF), orchestration, CLI `build`.

## Non-goals (permanent)

- No scraping or remote content fetch.
- No DRM circumvention.
- No mandatory cloud services.
