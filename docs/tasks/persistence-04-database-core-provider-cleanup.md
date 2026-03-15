---
title: "Execution Task 4: Database Core Provider Cleanup"
document_type: "task"
depends_on:
  - "./persistence-01-remove-unsupported-tiered-surface.md"
  - "./persistence-02-database-cache-isolation.md"
  - "./persistence-03-database-bounded-context-refactor.md"
umbrella_task: "./refactor-persistence-bounded-contexts.md"
---

# Task 4: Database Core Provider Cleanup

## Objective

Finish the database refactor by making `database_core` slimmer and more provider-focused while preserving the supported non-tiered runtime behavior.

## Meaningful End State

After this task:

- `database_core` is cleaner and more focused on provider/runtime concerns;
- `database` depends on a simpler lower layer;
- the database stack is modularized without broadening scope to unrelated packages.

## Scope Rules

- Keep work centered on `packages/database_core`, with only necessary companion changes in `packages/database`.
- Do not use this task to redesign `core` or `sampling`.
- Preserve the existing supported physical schema.

## Required Context

### Read First

- `docs/tasks/refactor-persistence-bounded-contexts.md`
- `packages/database_core/docs/module-spec.md`
- `packages/database/docs/module-spec.md`

### Files To Read First

- `packages/database_core/src/nl_processing/database_core/backend/abstract.py`
- `packages/database_core/src/nl_processing/database_core/backend/neon.py`
- `packages/database_core/src/nl_processing/database_core/_database_config.py`
- `packages/database_core/src/nl_processing/database_core/backend/_queries.py`
- `packages/database_core/src/nl_processing/database_core/backend/_queries_detailed.py`
- `packages/database_core/src/nl_processing/database_core/backend/_queries_delete.py`
- refactored `database` internals from Task 3

## Work Items

### 1. Slim the provider-facing layer

Reduce `database_core` internals so they are easier to reason about as a provider/runtime layer:

- connection lifecycle
- configuration
- generic query execution helpers
- schema/bootstrap helpers
- generic storage exceptions

### 2. Remove abandoned tiered remnants from lower layers

Ensure no tiered persistence support remains in `database_core` after this cleanup.

### 3. Tighten the boundary with `database`

Make the `database` to `database_core` boundary cleaner and easier to maintain, without turning this into a repo-wide contract redesign.

### 4. Preserve supported schema bootstrap behavior

Supported non-tiered table creation and lower-layer runtime behavior must remain intact.

## Expected Files To Change

- `packages/database_core/src/nl_processing/database_core/backend/abstract.py`
- `packages/database_core/src/nl_processing/database_core/backend/neon.py`
- `packages/database_core/src/nl_processing/database_core/_database_config.py`
- `packages/database_core/src/nl_processing/database_core/backend/_queries.py`
- `packages/database_core/src/nl_processing/database_core/backend/_queries_detailed.py`
- `packages/database_core/src/nl_processing/database_core/backend/_queries_delete.py`
- additional small helper modules inside `packages/database_core/src/nl_processing/database_core/` if needed
- companion integration points inside `packages/database/src/nl_processing/database/`
- `packages/database_core/tests/integration/database_core/`
- `packages/database/tests/integration/database/`

## Acceptance Criteria

- `database_core` is slimmer and more provider-focused than the current shape;
- tiered persistence remnants are fully gone from `database_core`;
- supported non-tiered schema bootstrap and runtime behavior remain intact;
- `packages/database_core` and `packages/database` checks are green.

## Verification

Run:

```bash
cd packages/database_core && make check
cd packages/database && make check
cd packages/database_cache && make check
```
