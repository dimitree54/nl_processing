---
title: "Execution Task 5: Database Core Thin Provider Layer"
document_type: "task"
depends_on:
  - "./persistence-01-shared-contract-foundation.md"
  - "./persistence-02-tiered-domain-and-sampling-cleanup.md"
  - "./persistence-03-cache-protocolization.md"
  - "./persistence-04-database-bounded-context-split.md"
umbrella_task: "./refactor-persistence-bounded-contexts.md"
---

# Task 5: Database Core Thin Provider Layer

## Objective

Finish the persistence refactor by reducing `database_core` to a thin storage/provider layer and migrating `database` repositories to low-level storage primitives instead of a fat domain-shaped backend contract.

This task completes the target architecture from the umbrella plan.

## Meaningful End State

After this task:

- `database_core` owns only provider/runtime mechanics;
- `database` owns domain repositories and domain SQL mapping;
- the fat `AbstractBackend` pattern is gone from the final architecture;
- the overall persistence stack is fully modularized while preserving one physical database and current public entrypoints.

## Scope

### In Scope

- redesign `database_core` into thin execution/bootstrap/transaction primitives;
- migrate `database` repositories to consume that new low-level provider layer;
- remove transitional backend-domain coupling introduced by the old `AbstractBackend` shape.

### Out Of Scope

- new physical schema design;
- additional package splitting outside the current package set.

## Required Context

### Read First

- `docs/tasks/refactor-persistence-bounded-contexts.md`
- `docs/tasks/persistence-04-database-bounded-context-split.md`
- `packages/database_core/docs/module-spec.md`
- `packages/database/docs/module-spec.md`

### Files To Read First

- `packages/database_core/src/nl_processing/database_core/backend/abstract.py`
- `packages/database_core/src/nl_processing/database_core/backend/neon.py`
- `packages/database_core/src/nl_processing/database_core/_database_config.py`
- `packages/database_core/src/nl_processing/database_core/backend/_queries.py`
- `packages/database_core/src/nl_processing/database_core/backend/_queries_detailed.py`
- `packages/database_core/src/nl_processing/database_core/backend/_queries_delete.py`
- `packages/database_core/src/nl_processing/database_core/backend/_tiered_queries.py`
- the new bounded-context repository modules created in Task 4

### Relevant Skills

- `feature-request`

## API References

### `asyncpg`

Use explicit transactions for atomic multi-step mutations.

Reference:

- [https://magicstack.github.io/asyncpg/current/usage.html](https://magicstack.github.io/asyncpg/current/usage.html)

The final provider layer must expose generic transaction/execution primitives, not domain verbs.

## Work Items

### 1. Replace fat backend contract with thin provider/runtime primitives

Refactor `database_core` into provider-focused modules such as:

- `connection.py`
- `executor.py`
- `transactions.py`
- `table_names.py`
- `schema.py`
- `backend/neon.py`

The new provider layer should own:

- connection lifecycle
- SQL execution primitives
- explicit transactions
- table/bootstrap orchestration
- generic provider exceptions

It must not own word/progress/detail domain operations.

### 2. Move domain SQL ownership into `database` repositories

Migrate the bounded-context repositories created in Task 4 so they own:

- domain queries
- row mapping
- DTO reconstruction
- domain-specific atomic mutation orchestration

They should consume low-level provider primitives from `database_core`.

### 3. Remove transitional backend-domain coupling

After repository migration:

- remove or collapse the old fat backend abstraction;
- keep compatibility only where required for public imports;
- avoid leaving both architectures alive in parallel.

### 4. Preserve schema/bootstrap behavior

Keep schema bootstrap idempotent for the unchanged table families:

- `words_<lang>`
- `translations_<src>_<tgt>`
- `user_words`
- `user_word_exercise_scores_<src>_<tgt>_<exercise>`
- `applied_events_<src>_<tgt>`
- `word_details_<src>_<tgt>`
- `user_word_tiered_repeat_state_<src>_<tgt>`

## Expected Files To Change

- `packages/database_core/src/nl_processing/database_core/backend/abstract.py`
- `packages/database_core/src/nl_processing/database_core/backend/neon.py`
- `packages/database_core/src/nl_processing/database_core/_database_config.py`
- `packages/database_core/src/nl_processing/database_core/backend/_queries.py`
- `packages/database_core/src/nl_processing/database_core/backend/_queries_detailed.py`
- `packages/database_core/src/nl_processing/database_core/backend/_queries_delete.py`
- `packages/database_core/src/nl_processing/database_core/backend/_tiered_queries.py`
- new thin provider/runtime modules under `packages/database_core/src/nl_processing/database_core/`
- bounded-context repository modules in `packages/database/src/nl_processing/database/`
- `packages/database_core/tests/integration/database_core/`
- `packages/database/tests/unit/database/`
- `packages/database/tests/integration/database/`

## Acceptance Criteria

- `database_core` no longer exposes one fat domain-shaped backend contract as the primary architecture;
- `database_core` owns provider/runtime mechanics only;
- `database` bounded-context repositories own domain query and row-mapping logic;
- atomic remote mutations use explicit transactions over provider primitives;
- schema/bootstrap behavior remains idempotent for the existing table families;
- current public database service import paths remain valid;
- `packages/database_core` and `packages/database` checks are green.

## Verification

Run:

```bash
cd packages/database_core && make check
cd packages/database && make check
cd packages/database_cache && make check
cd packages/core && make check
cd packages/sampling && make check
```

This final task must leave the whole refactor series fully integrated, not only locally green in `database_core`.
