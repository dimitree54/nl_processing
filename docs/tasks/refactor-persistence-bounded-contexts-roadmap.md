---
title: "Roadmap: Refactor Database Modules"
document_type: "task-roadmap"
umbrella_task: "./refactor-persistence-bounded-contexts.md"
---

# Roadmap: Refactor Database Modules

## Purpose

This roadmap breaks the database refactor into focused execution tasks. Each task must leave the repository in a meaningful working state.

The series is intentionally scoped to:

- `packages/database_core`
- `packages/database`
- `packages/database_cache`

External modules should remain largely untouched.

## Execution Order

### Task 1

- `docs/tasks/persistence-01-remove-unsupported-tiered-surface.md`

Outcome:

- tiered persistence/cache surface is removed from `database_*` code, tests, and docs;
- the supported target state becomes explicit before deeper refactoring starts.

### Task 2

- `docs/tasks/persistence-02-database-cache-isolation.md`

Outcome:

- `database_cache` is cleaned up around its supported non-tiered behavior;
- local cache internals become clearer and more self-contained without broad external refactors.

### Task 3

- `docs/tasks/persistence-03-database-bounded-context-refactor.md`

Outcome:

- `database` stops behaving like one god-module internally;
- public non-tiered facades stay stable.

### Task 4

- `docs/tasks/persistence-04-database-core-provider-cleanup.md`

Outcome:

- `database_core` is reduced to a slimmer provider/runtime layer;
- the full non-tiered database refactor target is implemented.

## Rules For All Tasks

- Keep scope centered on `database_*`.
- Prefer adapting `database_*` to the existing state of `core`, `sampling`, `translate_*`, and `extract_*`.
- Remove unsupported tiered persistence/cache code rather than repairing or extending it.
- Keep package-local `make check` green for every touched package.
