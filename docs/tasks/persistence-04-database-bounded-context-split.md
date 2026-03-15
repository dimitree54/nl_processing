---
title: "Execution Task 4: Database Bounded-Context Split"
document_type: "task"
depends_on:
  - "./persistence-01-shared-contract-foundation.md"
  - "./persistence-02-tiered-domain-and-sampling-cleanup.md"
  - "./persistence-03-cache-protocolization.md"
next_task: "./persistence-05-database-core-thin-provider-layer.md"
umbrella_task: "./refactor-persistence-bounded-contexts.md"
---

# Task 4: Database Bounded-Context Split

## Objective

Refactor `database` so it stops being a god-module internally and becomes a set of bounded-context repositories and application services behind stable public facades.

This task should preserve runtime behavior and current public APIs while changing the internal structure.

## Meaningful End State

After this task:

- `database` is internally decomposed by responsibility;
- the main public service classes become thin facades;
- storage concerns, orchestration concerns, and DTO shaping are separated;
- current remote behavior remains intact.

## Scope

### In Scope

- split `database` by bounded context:
  - lexicon
  - user vocabulary
  - generic progress
  - detailed records
  - tiered progress
- move translator/extractor orchestration into thin application services;
- keep current public class import paths stable.

### Out Of Scope

- `database_core` redesign in this task;
- physical schema changes;
- cache redesign beyond adapting to new public/internal database structure if needed.

## Required Context

### Read First

- `docs/tasks/refactor-persistence-bounded-contexts.md`
- `packages/database/docs/module-spec.md`

### Files To Read First

- `packages/database/src/nl_processing/database/__init__.py`
- `packages/database/src/nl_processing/database/service.py`
- `packages/database/src/nl_processing/database/exercise_progress.py`
- `packages/database/src/nl_processing/database/detailed_store.py`
- `packages/database/src/nl_processing/database/tiered_progress.py`
- `packages/database/src/nl_processing/database/_service_helpers.py`
- `packages/database/src/nl_processing/database/_progress_helpers.py`
- `packages/database/src/nl_processing/database/_translation.py`
- `packages/database/src/nl_processing/database/_tiered_backend_ops.py`
- `packages/database/tests/unit/database/`
- `packages/database/tests/integration/database/`
- `packages/database/tests/e2e/database/`

### Relevant Skills

- `feature-request`

## Work Items

### 1. Create bounded-context internal structure

Introduce internal subpackages for:

- `lexicon/`
- `user_vocabulary/`
- `progress/`
- `details/`
- `tiered/`

Each subpackage should own its own persistence mapping and local domain logic for that context.

### 2. Turn public classes into thin facades

Keep these public classes:

- `DatabaseService`
- `ExerciseProgressStore`
- `DetailedWordStore`
- `TieredExerciseProgressStore`

Refactor them so they compose context-specific repositories/application services rather than containing the logic directly.

### 3. Separate orchestration from persistence

Move cross-module orchestration into thin application services:

- word translation materialization
- detailed-record extraction materialization

Repositories should persist/fetch state. They should not own translator/extractor workflow logic.

### 4. Preserve physical schema and stable ids

Keep the existing table families, joins, stable ids, and SQL semantics intact in this task.

This is a code-structure change, not a schema redesign.

## Expected Files To Change

- `packages/database/src/nl_processing/database/__init__.py`
- `packages/database/src/nl_processing/database/service.py`
- `packages/database/src/nl_processing/database/exercise_progress.py`
- `packages/database/src/nl_processing/database/detailed_store.py`
- `packages/database/src/nl_processing/database/tiered_progress.py`
- `packages/database/src/nl_processing/database/_service_helpers.py`
- `packages/database/src/nl_processing/database/_progress_helpers.py`
- `packages/database/src/nl_processing/database/_translation.py`
- `packages/database/src/nl_processing/database/_tiered_backend_ops.py`
- new bounded-context subpackages under `packages/database/src/nl_processing/database/`
- `packages/database/tests/unit/database/`
- `packages/database/tests/integration/database/`
- `packages/database/tests/e2e/database/`

## Acceptance Criteria

- `database` internal code is split by bounded context instead of centered around god-module service files;
- public import paths for `DatabaseService`, `ExerciseProgressStore`, `DetailedWordStore`, and `TieredExerciseProgressStore` remain valid;
- public behavior stays consistent with existing module specs;
- translator/extractor orchestration is separated from persistence repositories;
- current table families and SQL join-based read models are preserved;
- `packages/database` check is green.

## Verification

Run:

```bash
cd packages/database && make check
```

Add targeted tests proving the facades still expose the same public behavior after the internal split.
