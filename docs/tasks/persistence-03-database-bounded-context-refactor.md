---
title: "Execution Task 3: Database Bounded-Context Refactor"
document_type: "task"
depends_on:
  - "./persistence-01-remove-unsupported-tiered-surface.md"
  - "./persistence-02-database-cache-isolation.md"
next_task: "./persistence-04-database-core-provider-cleanup.md"
umbrella_task: "./refactor-persistence-bounded-contexts.md"
---

# Task 3: Database Bounded-Context Refactor

## Objective

Refactor `database` so the package stops behaving like one god-module internally while keeping the current supported non-tiered public surfaces intact.

## Meaningful End State

After this task:

- `database` is internally broken into smaller bounded responsibilities;
- public non-tiered facades remain the same;
- storage logic, orchestration logic, and DTO shaping are less tangled.

## Scope Rules

- Keep work centered on `packages/database`.
- Do not treat this task as a repo-wide shared-contract redesign.
- Adapt `database` to the current state of external modules rather than broadening scope outward.

## Required Context

### Read First

- `docs/tasks/refactor-persistence-bounded-contexts.md`
- `packages/database/docs/module-spec.md`

### Files To Read First

- `packages/database/src/nl_processing/database/service.py`
- `packages/database/src/nl_processing/database/exercise_progress.py`
- `packages/database/src/nl_processing/database/detailed_store.py`
- `packages/database/src/nl_processing/database/_service_helpers.py`
- `packages/database/src/nl_processing/database/_progress_helpers.py`
- `packages/database/src/nl_processing/database/_translation.py`
- `packages/database/src/nl_processing/database/models.py`
- `packages/database/src/nl_processing/database/detailed_models.py`
- `packages/database/tests/unit/database/`
- `packages/database/tests/integration/database/`
- `packages/database/tests/e2e/database/`

## Work Items

### 1. Split internal responsibilities

Introduce a cleaner internal structure for supported non-tiered concerns such as:

- canonical words and translations
- user vocabulary membership and delete logic
- exercise progress
- detailed-word persistence and read-through extraction

### 2. Turn public classes into thin facades

Keep the supported public entrypoints stable:

- `DatabaseService`
- `ExerciseProgressStore`
- `DetailedWordStore`

Move heavy logic out of these files into smaller internal components.

### 3. Separate orchestration from persistence

Keep repository/storage logic focused on persistence.

Keep translation/extraction orchestration in thin service/application layers inside `database` where needed.

### 4. Preserve current physical schema

This is a code-structure refactor, not a physical schema redesign.

Keep current supported table families and stable ids intact.

## Expected Files To Change

- `packages/database/src/nl_processing/database/service.py`
- `packages/database/src/nl_processing/database/exercise_progress.py`
- `packages/database/src/nl_processing/database/detailed_store.py`
- `packages/database/src/nl_processing/database/_service_helpers.py`
- `packages/database/src/nl_processing/database/_progress_helpers.py`
- `packages/database/src/nl_processing/database/_translation.py`
- `packages/database/src/nl_processing/database/models.py`
- `packages/database/src/nl_processing/database/detailed_models.py`
- new internal subpackages or helper modules under `packages/database/src/nl_processing/database/`
- `packages/database/tests/unit/database/`
- `packages/database/tests/integration/database/`
- `packages/database/tests/e2e/database/`

## Acceptance Criteria

- `database` no longer concentrates most supported behavior in a few god-module files;
- supported public entrypoints remain stable;
- translator/extractor orchestration is separated from lower-level persistence work;
- physical schema and stable ids for supported features remain intact;
- `packages/database` check is green.

## Verification

Run:

```bash
cd packages/database && make check
```
