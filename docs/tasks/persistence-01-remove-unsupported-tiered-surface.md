---
title: "Execution Task 1: Remove Unsupported Tiered Surface"
document_type: "task"
depends_on: []
next_task: "./persistence-02-database-cache-isolation.md"
umbrella_task: "./refactor-persistence-bounded-contexts.md"
---

# Task 1: Remove Unsupported Tiered Surface

## Objective

Remove the abandoned tiered persistence/cache surface from `database_core`, `database`, and `database_cache`.

Tiered persistence was planned but never became a supported, working feature. It must not remain in code, tests, docs, or future refactor plans for `database_*`.

## Meaningful End State

After this task:

- `database_*` packages expose only supported non-tiered persistence/cache APIs;
- tiered runtime code is removed;
- tiered tests are removed;
- database module specs no longer describe tiered behavior as planned or supported.

## Scope

### In Scope

- remove tiered-only code from `database_core`, `database`, and `database_cache`;
- remove tiered-only tests from those packages;
- update `database` and `database_cache` module specs to mark tiered behavior as out of scope and unsupported;
- update refactor task docs so they no longer plan tiered implementation.

### Out Of Scope

- cleanup of unrelated sampling tiered logic;
- cleanup of non-database module docs;
- broader architectural refactors beyond removing unsupported tiered persistence/cache code.

## Required Context

### Read First

- `docs/tasks/refactor-persistence-bounded-contexts.md`
- `packages/database/docs/module-spec.md`
- `packages/database_cache/docs/module-spec.md`

### Files To Read First

- `packages/database/src/nl_processing/database/__init__.py`
- `packages/database/src/nl_processing/database/tiered_progress.py`
- `packages/database/src/nl_processing/database/tiered_models.py`
- `packages/database/src/nl_processing/database/_tiered_helpers.py`
- `packages/database/src/nl_processing/database/_tiered_backend_ops.py`
- `packages/database/src/nl_processing/database/backend/_neon_tiered.py`
- `packages/database/src/nl_processing/database/backend/_tiered_queries.py`
- `packages/database_cache/src/nl_processing/database_cache/tiered_cache.py`
- `packages/database_cache/src/nl_processing/database_cache/tiered_sync.py`
- `packages/database_cache/src/nl_processing/database_cache/_tiered_helpers.py`
- `packages/database_cache/src/nl_processing/database_cache/_tiered_cache_helpers.py`
- `packages/database_cache/src/nl_processing/database_cache/_tiered_local_store.py`
- `packages/database_cache/src/nl_processing/database_cache/_tiered_queries.py`
- `packages/database_cache/src/nl_processing/database_cache/_tiered_result_recorder.py`
- `packages/database_core/src/nl_processing/database_core/backend/_neon_tiered.py`
- `packages/database_core/src/nl_processing/database_core/backend/_tiered_queries.py`

## Work Items

### 1. Remove tiered exports and runtime files

Delete the tiered-only runtime surface from `database_*`.

Examples include:

- tiered store/service classes
- tiered helper/state-machine modules
- tiered query modules
- tiered backend support modules
- tiered cache sync/local-store modules

### 2. Remove tiered tests

Delete tiered-only unit/integration tests from the affected database packages.

Do not replace them. Tiered persistence is no longer part of the supported target state.

### 3. Remove tiered docs from `database_*`

Update:

- `packages/database/docs/module-spec.md`
- `packages/database_cache/docs/module-spec.md`

Required docs outcome:

- tiered persistence/cache behavior is no longer described as a future supported extension;
- out-of-scope sections explicitly say tiered persistence/cache is unsupported.

### 4. Remove tiered planning from refactor docs

Update the database refactor task docs so they no longer plan to build or preserve tiered persistence/cache features.

## Expected Files To Change

- tiered runtime files under:
  - `packages/database_core/src/nl_processing/database_core/`
  - `packages/database/src/nl_processing/database/`
  - `packages/database_cache/src/nl_processing/database_cache/`
- tiered tests under:
  - `packages/database/tests/`
  - `packages/database_cache/tests/`
- docs:
  - `packages/database/docs/module-spec.md`
  - `packages/database_cache/docs/module-spec.md`
  - `docs/tasks/refactor-persistence-bounded-contexts.md`
  - `docs/tasks/refactor-persistence-bounded-contexts-roadmap.md`

## Acceptance Criteria

- no supported `database_*` package exports a tiered persistence/cache class;
- tiered runtime files are removed from `database_*`;
- tiered tests are removed from `database_*`;
- `database` and `database_cache` module specs no longer describe tiered extensions as supported or planned;
- the remaining non-tiered database packages still import and run cleanly.

## Verification

Run:

```bash
cd packages/database_core && make check
cd packages/database && make check
cd packages/database_cache && make check
```
