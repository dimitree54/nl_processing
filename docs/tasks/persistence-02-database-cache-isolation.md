---
title: "Execution Task 2: Database Cache Isolation"
document_type: "task"
depends_on:
  - "./persistence-01-remove-unsupported-tiered-surface.md"
next_task: "./persistence-03-database-bounded-context-refactor.md"
umbrella_task: "./refactor-persistence-bounded-contexts.md"
---

# Task 2: Database Cache Isolation

## Objective

Refactor `database_cache` around its supported non-tiered surfaces only:

- practice cache
- detailed-word cache

The goal is to make the package more internally modular and easier to maintain without using this task to refactor unrelated modules.

## Meaningful End State

After this task:

- `database_cache` contains only supported non-tiered cache logic;
- practice-cache and detailed-cache responsibilities are clearer internally;
- local schema and cache lifecycle behavior are explicit and easier to reason about.

## Scope Rules

- Keep changes inside `packages/database_cache` whenever possible.
- If a small compatibility tweak outside `database_cache` is unavoidable, keep it minimal and directly justified.
- Do not open refactor work in `core`, `sampling`, `translate_*`, or `extract_*` unless strictly necessary.

## Required Context

### Read First

- `docs/tasks/refactor-persistence-bounded-contexts.md`
- `docs/tasks/persistence-01-remove-unsupported-tiered-surface.md`
- `packages/database_cache/docs/module-spec.md`

### Files To Read First

- `packages/database_cache/src/nl_processing/database_cache/service.py`
- `packages/database_cache/src/nl_processing/database_cache/detailed_cache.py`
- `packages/database_cache/src/nl_processing/database_cache/sync.py`
- `packages/database_cache/src/nl_processing/database_cache/local_store.py`
- `packages/database_cache/src/nl_processing/database_cache/_local_store_base.py`
- `packages/database_cache/src/nl_processing/database_cache/_service_helpers.py`
- `packages/database_cache/src/nl_processing/database_cache/_detailed_local_store.py`
- `packages/database_cache/src/nl_processing/database_cache/_detailed_queries.py`
- `packages/database_cache/tests/unit/database_cache/`
- `packages/database_cache/tests/integration/database_cache/`

## Work Items

### 1. Isolate supported cache slices

Make the package structure and internal code clearly reflect the two supported slices:

- practice cache
- detailed-word cache

Reduce cross-talk between unrelated helper files where possible.

### 2. Make local schema handling explicit

Audit local SQLite schema bootstrap and migration behavior in supported code paths.

Remove hidden or ambiguous behavior where practical. Prefer explicit schema/version handling or explicit failure.

### 3. Keep remote interaction boundaries explicit

Keep remote sync/delete/read-through dependencies explicit and well-contained.

This task may improve dependency injection and internal builder placement inside `database_cache`, but it should not trigger a large shared-contract redesign outside `database_*`.

### 4. Preserve existing supported behavior

Maintain:

- warm local reads;
- local-first score writes plus pending-event outbox;
- background refresh/flush behavior;
- remote-first delete behavior;
- pair-scoped detailed read-through cache behavior.

## Expected Files To Change

- `packages/database_cache/src/nl_processing/database_cache/service.py`
- `packages/database_cache/src/nl_processing/database_cache/detailed_cache.py`
- `packages/database_cache/src/nl_processing/database_cache/sync.py`
- `packages/database_cache/src/nl_processing/database_cache/local_store.py`
- `packages/database_cache/src/nl_processing/database_cache/_local_store_base.py`
- `packages/database_cache/src/nl_processing/database_cache/_service_helpers.py`
- `packages/database_cache/src/nl_processing/database_cache/_detailed_local_store.py`
- `packages/database_cache/src/nl_processing/database_cache/_detailed_queries.py`
- `packages/database_cache/tests/unit/database_cache/`
- `packages/database_cache/tests/integration/database_cache/`
- `packages/database_cache/tests/e2e/database_cache/`

## Acceptance Criteria

- `database_cache` contains only supported non-tiered runtime surfaces;
- practice and detailed cache slices are clearer and more isolated internally;
- local schema handling in supported paths is explicit and fail-fast where necessary;
- current supported cache behavior is preserved;
- `packages/database_cache` check is green.

## Verification

Run:

```bash
cd packages/database_cache && make check
```
