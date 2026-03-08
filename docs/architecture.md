# Architecture Decision Document - nl_processing (Shared)

## Current State

`nl_processing` is a multi-package Python monorepo.

The repo root is responsible for:

- aggregate packaging of the published `nl_processing` distribution;
- shared documentation;
- repo-wide lint/test automation.

Each module under `packages/` is a standalone Python project for day-to-day development.

## Repository Layout

```text
repo/
  docs/
  packages/
    core/
      src/nl_processing/core/
      tests/
      docs/
      pyproject.toml
    extract_text_from_image/
    extract_words_from_text/
    translate_text/
    translate_word/
    database/
    database_cache/
    sampling/
  pyproject.toml
  ruff.toml
  Makefile
```

## Architectural Decisions

### Decision: Per-Module Projects Inside One Repo

Each module is developed as its own project:

- package-local `pyproject.toml`;
- package-local `ruff.toml`;
- package-local `pytest.ini`;
- package-local `tests/`.

This keeps module work isolated without losing a shared repository for docs, CI, and aggregate distribution.

### Decision: `core` Owns Shared Public Types

Shared DTOs that cross package boundaries live in `nl_processing.core.models`.

Current shared models include:

- `Language`
- `PartOfSpeech`
- `ExtractedText`
- `Word`
- `WordPair`
- `ScoredWordPair`

This prevents unrelated packages from depending on `database.models` just to exchange common typed payloads.

### Decision: Explicit Cross-Package Dependencies

Cross-package imports are allowed only when backed by explicit package dependencies.

Examples:

- `database_cache -> database`
- `sampling -> database` for the default progress-store implementation
- `translate_* -> core`
- `extract_* -> core`

### Decision: Composition Instead of Hidden Orchestration

The repo avoids hidden package orchestration where possible.

Most important example:

- old design: `database` directly imported and constructed `translate_word.WordTranslator`
- current design: `database` accepts an injected translator dependency

That keeps `database` usable as an independent package while still allowing higher-level flows to opt into automatic translation.

### Decision: Root Project Is Aggregate, Not The Development Boundary

The root `pyproject.toml` exists to:

- build the aggregate `nl_processing` distribution;
- support root-level linting and packaging;
- preserve the published package flow.

It is not the only project in the repo anymore.

## Tooling Model

### Package-Local Development

Typical flow:

```bash
cd packages/translate_word
uv sync --all-groups
uv run pytest tests/unit
```

### Repo-Wide Checks

The root `Makefile` runs:

- ruff on `packages/`
- pylint on `packages/`
- vulture on `packages/`
- jscpd on `packages/`
- per-package unit/integration/e2e test runs

## Testing Model

Tests live with the owning package.

Examples:

- `packages/core/tests/unit/...`
- `packages/database/tests/integration/...`
- `packages/database_cache/tests/e2e/...`

This avoids a shared root test tree and lets developers run tests from within the package they are changing.

## Dependency Guidance

Use these rules before introducing a new package dependency:

1. If the dependency is only a shared DTO or exception, move it to `core`.
2. If the dependency is orchestration rather than domain ownership, inject it.
3. If the dependency is an intentional facade relationship, keep it explicit in package metadata.

## Documentation Guidance

Shared repo-level concepts live in `docs/`.

Package-specific behavior, requirements, and architecture live in `packages/<module>/docs/`.
