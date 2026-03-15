---
title: "Roadmap: Refactor Persistence Stack Into Bounded Contexts"
document_type: "task-roadmap"
umbrella_task: "./refactor-persistence-bounded-contexts.md"
---

# Roadmap: Refactor Persistence Stack Into Bounded Contexts

## Purpose

This roadmap splits the umbrella persistence refactor into focused execution tasks. The tasks must be implemented in order. After each task:

- the repository remains working;
- affected package checks are green;
- the system gains a meaningful architectural improvement rather than a half-migrated intermediate state.

Use this roadmap for execution order. Use the umbrella task for the full target architecture and cross-cutting rationale:

- `docs/tasks/refactor-persistence-bounded-contexts.md`

## Execution Order

### Task 1

- `docs/tasks/persistence-01-shared-contract-foundation.md`

Outcome:

- shared persistence ports and DTOs exist in `core`;
- current contract drift is repaired;
- existing public import paths continue to work through compatibility re-exports.

### Task 2

- `docs/tasks/persistence-02-tiered-domain-and-sampling-cleanup.md`

Outcome:

- one shared tiered repeat-state implementation exists;
- remote/cache tiered logic uses the same state machine;
- `sampling` is aligned to its documented algorithm-only contract.

### Task 3

- `docs/tasks/persistence-03-cache-protocolization.md`

Outcome:

- `database_cache` is driven by shared ports and models, not concrete `database` classes;
- local schema handling becomes explicit and fail-fast;
- cache behavior remains working and validated.

### Task 4

- `docs/tasks/persistence-04-database-bounded-context-split.md`

Outcome:

- `database` stops being a god-module internally;
- bounded-context repositories/application services exist behind stable public facades;
- current runtime behavior remains intact.

### Task 5

- `docs/tasks/persistence-05-database-core-thin-provider-layer.md`

Outcome:

- `database_core` is reduced to a thin provider/runtime layer;
- `database` repositories consume low-level storage primitives rather than a fat domain backend;
- the full target architecture from the umbrella task is implemented.

## Rules For All Tasks

- Do not split the physical PostgreSQL database.
- Do not rename current table families in this refactor series.
- Preserve current public service import paths.
- Keep every touched package green with its own `make check`.
- Stop and report any code/spec contradiction before changing behavior.
