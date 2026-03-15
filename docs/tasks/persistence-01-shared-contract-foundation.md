---
title: "Execution Task 1: Shared Contract Foundation"
document_type: "task"
depends_on: []
next_task: "./persistence-02-tiered-domain-and-sampling-cleanup.md"
umbrella_task: "./refactor-persistence-bounded-contexts.md"
---

# Task 1: Shared Contract Foundation

## Objective

Create the shared persistence contract layer in `core` and migrate the current codebase to consume it without changing user-visible behavior.

This task exists to repair the current contract drift before deeper refactoring begins.

## Meaningful End State

After this task:

- `core` owns the shared ports and DTOs that multiple packages use;
- `database`, `database_cache`, and `sampling` compile against one consistent shared contract layer;
- broken/missing tiered import paths are fixed;
- existing public import paths remain valid through compatibility re-exports.

The runtime behavior should remain effectively unchanged.

## Scope

### In Scope

- add shared persistence ports and DTOs to `core`;
- add compatibility re-exports so existing imports keep working;
- update consumers to use the shared `core` contracts;
- repair current broken import paths and shared-contract drift.

### Out Of Scope

- bounded-context decomposition inside `database`;
- `database_core` backend redesign;
- `database_cache` architectural cleanup beyond switching to shared DTOs/ports;
- tiered state-machine unification beyond what is required for contracts to compile.

## Required Context

### Read First

- `README.md`
- `docs/module-spec.md`
- `docs/tasks/refactor-persistence-bounded-contexts.md`
- `packages/core/docs/module-spec.md`
- `packages/database/docs/module-spec.md`
- `packages/database_cache/docs/module-spec.md`
- `packages/sampling/docs/module-spec.md`

### Files To Read First

- `packages/core/src/nl_processing/core/models.py`
- `packages/core/src/nl_processing/core/protocols.py`
- `packages/core/tests/unit/core/test_protocols.py`
- `packages/database/src/nl_processing/database/models.py`
- `packages/database/src/nl_processing/database/detailed_models.py`
- `packages/database/src/nl_processing/database/detailed_ports.py`
- `packages/database_cache/src/nl_processing/database_cache/service.py`
- `packages/database_cache/src/nl_processing/database_cache/sync.py`
- `packages/database_cache/src/nl_processing/database_cache/detailed_cache.py`
- `packages/database_cache/src/nl_processing/database_cache/detailed_ports.py`
- `packages/database_cache/src/nl_processing/database_cache/ports.py`
- `packages/database_cache/src/nl_processing/database_cache/tiered_cache.py`
- `packages/sampling/src/nl_processing/sampling/service.py`

### Relevant Skills

- `feature-request`
- `module-spec-agent`
  - only if implementation reveals a real code/spec conflict

## API References

### Python protocols

Use `Protocol` and `@runtime_checkable` for shared cross-package contracts.

Reference:

- [https://docs.python.org/3.12/library/typing.html](https://docs.python.org/3.12/library/typing.html)

Repo example:

- `packages/core/src/nl_processing/core/protocols.py`

## Work Items

### 1. Create real shared contract modules in `core`

Add the shared modules required by current repo docs and current package usage:

- `packages/core/src/nl_processing/core/ports.py`
- `packages/core/src/nl_processing/core/progress_ports.py`
- `packages/core/src/nl_processing/core/detail_ports.py`
- `packages/core/src/nl_processing/core/tiered_ports.py`
- `packages/core/src/nl_processing/core/progress_models.py`
- `packages/core/src/nl_processing/core/detail_models.py`
- `packages/core/src/nl_processing/core/tiered_models.py`

Move or re-home the following shared types into `core`:

- `PersonalWord`
- `ExerciseProgressSummary`
- `EnrichedWordPairSnapshot`
- `DetailedWordRecord`
- `JsonValue`
- `TieredCandidate`
- `TieredProgressSummary`
- `TieredSnapshotEntry`
- `RemoteProgressSyncPort`
- `RemoteDeletePort`
- `RemoteDetailedWordStorePort`
- `SchemaVersionChecker` if it remains a cross-package concern
- tiered sync/candidate ports

### 2. Preserve old import paths with re-exports

Keep existing imports working where consumers are likely to still use them:

- `packages/core/src/nl_processing/core/protocols.py`
- `packages/database/src/nl_processing/database/models.py`
- `packages/database/src/nl_processing/database/detailed_models.py`
- `packages/database/src/nl_processing/database/detailed_ports.py`
- `packages/database_cache/src/nl_processing/database_cache/ports.py`
- `packages/database_cache/src/nl_processing/database_cache/detailed_ports.py`

The re-export modules may remain thin compatibility layers after this task.

### 3. Repair current broken import graph

Fix the currently inconsistent references so the tree reflects the actual shared contract layer:

- create the missing `core` tiered modules used by cache and future consumers;
- fix imports that point to non-existent modules;
- fix imports that expect shared ports to exist in `core.protocols` but do not.

### 4. Update consumers to use shared contracts

Switch the relevant runtime code to import shared DTOs and ports from `core` rather than package-local duplicates.

Affected consumer areas:

- `database_cache`
- `sampling`
- `database` compatibility re-exports and consumers

Do not change public behavior in this task. This is a contract-foundation task.

## Expected Files To Change

- `packages/core/src/nl_processing/core/__init__.py`
- `packages/core/src/nl_processing/core/protocols.py`
- new `core` port/model modules listed above
- `packages/core/tests/unit/core/`
- `packages/database/src/nl_processing/database/models.py`
- `packages/database/src/nl_processing/database/detailed_models.py`
- `packages/database/src/nl_processing/database/detailed_ports.py`
- `packages/database_cache/src/nl_processing/database_cache/service.py`
- `packages/database_cache/src/nl_processing/database_cache/sync.py`
- `packages/database_cache/src/nl_processing/database_cache/detailed_cache.py`
- `packages/database_cache/src/nl_processing/database_cache/tiered_cache.py`
- `packages/database_cache/src/nl_processing/database_cache/ports.py`
- `packages/database_cache/src/nl_processing/database_cache/detailed_ports.py`
- `packages/sampling/src/nl_processing/sampling/service.py`

## Acceptance Criteria

- `nl_processing.core.ports` exists.
- `database_cache` no longer imports shared DTOs from `database.models` or `database.detailed_models`.
- `database_cache` can import its shared progress and tiered ports from `core` without missing-module failures.
- the missing tiered `core` model/port modules exist and are used by current consumers.
- old public import paths keep working through compatibility re-exports.
- no user-visible runtime behavior is intentionally changed in this task.
- `packages/core`, `packages/database`, `packages/database_cache`, and `packages/sampling` package checks are green.

## Verification

Run:

```bash
cd packages/core && make check
cd packages/database && make check
cd packages/database_cache && make check
cd packages/sampling && make check
```

Also add protocol/model smoke tests proving the new shared import layer works from `core`.
