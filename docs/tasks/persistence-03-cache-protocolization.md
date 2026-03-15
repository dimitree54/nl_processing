---
title: "Execution Task 3: Database Cache Protocolization"
document_type: "task"
depends_on:
  - "./persistence-01-shared-contract-foundation.md"
  - "./persistence-02-tiered-domain-and-sampling-cleanup.md"
next_task: "./persistence-04-database-bounded-context-split.md"
umbrella_task: "./refactor-persistence-bounded-contexts.md"
---

# Task 3: Database Cache Protocolization

## Objective

Refactor `database_cache` so it becomes a real cache/decorator layer over shared ports and shared models, not a layer that knows concrete `database` service classes.

## Meaningful End State

After this task:

- `database_cache` core logic depends on shared `core` ports and models only;
- default remote composition, where still needed, lives in explicit builder modules;
- local SQLite schema handling is explicit and fail-fast instead of silent and fallback-like;
- current cache behavior remains working.

## Scope

### In Scope

- protocolize practice, detailed, and tiered cache services;
- isolate default remote builders from core cache service logic;
- remove concrete `database` imports from cache core logic;
- replace silent local schema fallback with explicit schema versioning/migration behavior.

### Out Of Scope

- full `database` bounded-context decomposition;
- `database_core` backend redesign.

## Required Context

### Read First

- `docs/tasks/refactor-persistence-bounded-contexts.md`
- `docs/tasks/persistence-01-shared-contract-foundation.md`
- `docs/tasks/persistence-02-tiered-domain-and-sampling-cleanup.md`
- `packages/database_cache/docs/module-spec.md`

### Files To Read First

- `packages/database_cache/src/nl_processing/database_cache/service.py`
- `packages/database_cache/src/nl_processing/database_cache/detailed_cache.py`
- `packages/database_cache/src/nl_processing/database_cache/tiered_cache.py`
- `packages/database_cache/src/nl_processing/database_cache/sync.py`
- `packages/database_cache/src/nl_processing/database_cache/tiered_sync.py`
- `packages/database_cache/src/nl_processing/database_cache/local_store.py`
- `packages/database_cache/src/nl_processing/database_cache/_local_store_base.py`
- `packages/database_cache/src/nl_processing/database_cache/_tiered_local_store.py`
- `packages/database_cache/tests/unit/database_cache/`
- `packages/database_cache/tests/integration/database_cache/`

### Relevant Skills

- `feature-request`

## API References

### `aiosqlite`

Use explicit open/execute/commit behavior and explicit schema handling. Do not hide migration errors.

Reference:

- [https://aiosqlite.omnilib.dev/en/latest/index.html](https://aiosqlite.omnilib.dev/en/latest/index.html)

Repo examples:

- `packages/database_cache/src/nl_processing/database_cache/_local_store_base.py`
- `packages/database_cache/src/nl_processing/database_cache/local_store.py`
- `packages/database_cache/src/nl_processing/database_cache/_tiered_local_store.py`

## Work Items

### 1. Remove concrete remote knowledge from cache service core logic

Refactor cache services so their core behavior consumes shared ports/models only:

- practice cache
- detailed-word cache
- tiered cache

Core cache service files must not import:

- `DatabaseService`
- `ExerciseProgressStore`
- `DetailedWordStore`
- DTO modules from `database`

### 2. Move default remote construction into explicit builder modules

If default remote composition is still needed for backwards compatibility, put it into explicit builder modules or factory functions. The runtime cache services should receive their dependencies via ports.

Do not keep lazy imports of concrete remote classes inside the main service classes.

### 3. Replace silent local schema fallback

Remove the current swallowed `ALTER TABLE` path from `_local_store_base.py`.

Replace it with explicit local schema versioning and one of:

- explicit migration applied and validated; or
- explicit failure that tells the caller the local cache schema is incompatible.

Do not silently ignore schema problems.

### 4. Keep current local-write and outbox semantics intact

Preserve:

- local-first score visibility;
- transactional local score write + pending event creation;
- refresh rebuild + pending-event reapply;
- remote-first delete semantics.

## Expected Files To Change

- `packages/database_cache/src/nl_processing/database_cache/service.py`
- `packages/database_cache/src/nl_processing/database_cache/detailed_cache.py`
- `packages/database_cache/src/nl_processing/database_cache/tiered_cache.py`
- `packages/database_cache/src/nl_processing/database_cache/sync.py`
- `packages/database_cache/src/nl_processing/database_cache/tiered_sync.py`
- `packages/database_cache/src/nl_processing/database_cache/local_store.py`
- `packages/database_cache/src/nl_processing/database_cache/_local_store_base.py`
- `packages/database_cache/src/nl_processing/database_cache/_tiered_local_store.py`
- new cache builder/default-composition modules
- `packages/database_cache/tests/unit/database_cache/`
- `packages/database_cache/tests/integration/database_cache/`
- `packages/database_cache/tests/e2e/database_cache/`

## Acceptance Criteria

- cache core logic no longer imports concrete `database` service/store classes;
- cache core logic no longer imports shared DTOs from `database` modules;
- any default remote wiring is isolated in explicit builder/factory modules;
- local schema handling is explicit and fail-fast;
- hot-path reads remain local after init/refresh;
- local write + outbox semantics remain unchanged;
- `packages/database_cache` check is green.

## Verification

Run:

```bash
cd packages/database_cache && make check
```

Also run targeted tests proving:

- refresh rebuild preserves ids, `added_at`, and scores;
- pending events are reapplied after refresh;
- incompatible local schema state fails explicitly instead of being silently swallowed.
