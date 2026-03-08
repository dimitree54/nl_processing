# Product Brief: nl_processing

## Executive Summary

`nl_processing` is a multi-package Python repository for Dutch language processing workflows powered by OpenAI models. The repo is intentionally split into independent packages so each module can be developed, tested, and versioned as its own project while still contributing to one larger toolkit.

The repository keeps:

- a shared `core` package for public data models, exceptions, and prompt helpers;
- independent domain packages under `packages/<module>`;
- an aggregate root package used for the published `nl_processing` distribution and repo-wide checks.

## Product Goal

Give an integration developer a set of small, composable Python modules that can be used independently or combined into a vocabulary-learning pipeline.

The primary workflow remains:

1. extract text from images;
2. extract normalized words from text;
3. translate words or text;
4. persist and score vocabulary remotely;
5. cache and sample practice data locally.

## Why The Repository Is Structured This Way

The previous single-package layout mixed together:

- one root `pyproject.toml`;
- one root `ruff.toml`;
- one root `tests/`;
- many modules that were mostly independent in runtime behavior.

That made day-to-day module development clumsy. The current structure optimizes for package-local work:

- `cd packages/<module>` feels like entering a standalone project;
- tests for a module live inside that module;
- package dependencies are explicit instead of being hidden by one shared source tree.

## Package Model

Every package under `packages/` contains:

- `src/nl_processing/<module>/...`
- `tests/`
- `docs/`
- `pyproject.toml`
- `ruff.toml`
- `pytest.ini`

The root repository still contains:

- shared documentation in `docs/`;
- aggregate build metadata in `pyproject.toml`;
- repo-wide automation via `Makefile` and GitHub Actions.

## Shared Design Principles

1. Small public APIs with typed results.
2. Explicit package dependencies instead of hidden coupling.
3. `core` owns shared public DTOs.
4. Package-local tests are the default development unit.
5. The root project is orchestration; packages are the development boundary.

## Important Dependency Decisions

- `core` remains the shared dependency layer.
- `database_cache` depends on `database` because it is explicitly a remote-cache facade.
- `sampling` may depend on `database` for the default remote progress source, but accepts an injected scored-store abstraction.
- `database` no longer directly constructs `translate_word.WordTranslator`; auto-translation is composed by the caller via dependency injection.

## Primary Audience

Python developers working inside this repo who want to iterate on one module at a time without carrying the entire repository structure in their head.
