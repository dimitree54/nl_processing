# Product Requirements Document - nl_processing (Shared)

## Scope

This document defines repository-wide requirements shared by every package in `nl_processing`.

Module-specific product behavior lives in `packages/<module>/docs/`.

## Shared Functional Requirements

### Repository Structure

- SR1: Every independent module lives in `packages/<module>`.
- SR2: Every module package has its own `pyproject.toml`, `ruff.toml`, `pytest.ini`, `tests/`, and `docs/`.
- SR3: The repo root may keep an aggregate `pyproject.toml` for the published `nl_processing` package and repo-wide tooling.
- SR4: Module-local tests must live inside the owning package, not in a shared root `tests/` tree.

### Shared Runtime Contracts

- SR5: Shared public DTOs live in `nl_processing.core.models`.
- SR6: Shared exceptions live in `nl_processing.core.exceptions`.
- SR7: Prompt loading helpers live in `nl_processing.core.prompts`.
- SR8: Cross-package imports must use the public `nl_processing.*` import path.

### Dependency Rules

- SR9: Package dependencies must be explicit in the consuming package's `pyproject.toml`.
- SR10: Avoid cross-package runtime coupling unless the dependency is part of the domain model.
- SR11: Optional orchestration dependencies must be injected rather than hard-coded where possible.
- SR12: `database` must not directly instantiate `translate_word`; callers compose that behavior explicitly.

### Testing

- SR13: Every package must be runnable from its own directory with package-local test commands.
- SR14: Repo-wide checks must still be available from the root.
- SR15: Unit, integration, and e2e tests remain separate quality gates.

## Shared Non-Functional Requirements

- SNFR1: Python 3.12+
- SNFR2: No relative imports
- SNFR3: Full type hints on public interfaces
- SNFR4: No silent env-var fallbacks
- SNFR5: Package-level development must be practical without editing root configs
- SNFR6: Shared tooling defaults may be inherited from the root, but each package must expose its own local config files

## Shared Paths

- Shared architecture: `docs/architecture.md`
- Shared product brief: `docs/product-brief.md`
- Shared env vars: `docs/ENV_VARS.md`
- Package docs: `packages/<module>/docs/`
