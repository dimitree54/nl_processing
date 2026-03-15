---
title: "Execution Task Series: Refactor Database Modules"
document_type: "task-series"
modules:
  - "database_core"
  - "database"
  - "database_cache"
source_specs:
  - "../module-spec.md"
  - "../../packages/database_core/docs/module-spec.md"
  - "../../packages/database/docs/module-spec.md"
  - "../../packages/database_cache/docs/module-spec.md"
---

# Refactor Database Modules

## Objective

Refactor `database_core`, `database`, and `database_cache` into a maintainable persistence stack without changing the physical PostgreSQL database layout.

The refactor series must also remove the abandoned tiered persistence/cache surface from `database_*`. Tiered persistence was planned, but it is not part of the supported target state and must not be implemented as part of this series.

## Scope Rules

- The primary scope is limited to:
  - `packages/database_core`
  - `packages/database`
  - `packages/database_cache`
- Changes in `core`, `sampling`, `translate_*`, and `extract_*` must be minimal.
- Do not use this series as an excuse to refactor external modules.
- If a database-module change can be implemented by adapting `database_*` to the existing external contract, prefer that over changing another package.
- If a tiny external compatibility adjustment becomes unavoidable, keep it minimal and directly justified by the database refactor.

## Target End State

After the full series:

- unsupported tiered persistence/cache code is removed from `database_*`;
- `database` remains the authoritative remote source of truth;
- `database_cache` remains the local cache/adapter layer;
- `database_core` is slimmer and more provider-focused;
- `database` is internally decomposed into smaller bounded responsibilities;
- the physical database schema and stable ids remain intact;
- public non-tiered entrypoints remain working.

## Fixed Decisions

- Keep one physical PostgreSQL database.
- Keep the current table families used by supported non-tiered features.
- Do not introduce a second database or per-feature databases.
- Do not implement the tiered repeat-state table or tiered cache flow.
- Remove tiered-only code, tests, and docs from `database_*`.
- Keep refactoring work concentrated in `database_*`.

## Working Sequence

Use the roadmap file for execution order:

- `docs/tasks/refactor-persistence-bounded-contexts-roadmap.md`

## Shared Acceptance Criteria For The Full Series

- `database_*` tiered code, tests, and docs are removed.
- `DatabaseService`, `ExerciseProgressStore`, `DetailedWordStore`, `DatabaseCacheService`, and `DetailedWordCacheService` remain supported.
- The current non-tiered physical schema stays intact.
- The refactor improves internal modularity without broadening scope to unrelated packages.
- Package-local checks are green for:
  - `packages/database_core`
  - `packages/database`
  - `packages/database_cache`
