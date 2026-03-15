---
title: "Execution Task 2: Tiered Domain Logic And Sampling Cleanup"
document_type: "task"
depends_on:
  - "./persistence-01-shared-contract-foundation.md"
next_task: "./persistence-03-cache-protocolization.md"
umbrella_task: "./refactor-persistence-bounded-contexts.md"
---

# Task 2: Tiered Domain Logic And Sampling Cleanup

## Objective

Move tiered repeat-state and tiered progress logic into one shared pure implementation and clean up `sampling` so it stays an algorithm-only package.

## Meaningful End State

After this task:

- the tiered repeat-state state machine exists in one shared pure module;
- both remote and cache tiered flows consume that same logic;
- `sampling` is aligned with its docs and contains only provider consumption, weighting, policy, and random choice logic.

This task delivers a meaningful working improvement even before the larger `database` and `database_core` decomposition is done.

## Scope

### In Scope

- shared pure tiered repeat-state logic;
- shared pure tiered progress aggregation logic;
- refactor remote/cache tiered callers to use the shared logic;
- clean up `sampling` internals and documented contract mismatches.

### Out Of Scope

- full `database_cache` protocolization;
- `database` bounded-context split;
- `database_core` backend redesign.

## Required Context

### Read First

- `docs/tasks/refactor-persistence-bounded-contexts.md`
- `docs/tasks/persistence-01-shared-contract-foundation.md`
- `packages/database/docs/module-spec.md`
- `packages/database_cache/docs/module-spec.md`
- `packages/sampling/docs/module-spec.md`

### Files To Read First

- `packages/database/src/nl_processing/database/_tiered_helpers.py`
- `packages/database/src/nl_processing/database/_tiered_backend_ops.py`
- `packages/database/src/nl_processing/database/tiered_progress.py`
- `packages/database_cache/src/nl_processing/database_cache/_tiered_helpers.py`
- `packages/database_cache/src/nl_processing/database_cache/_tiered_result_recorder.py`
- `packages/database_cache/src/nl_processing/database_cache/tiered_cache.py`
- `packages/database_cache/src/nl_processing/database_cache/tiered_sync.py`
- `packages/sampling/src/nl_processing/sampling/service.py`
- `packages/sampling/tests/unit/sampling/test_tiered_sampler_behavior.py`
- `packages/sampling/tests/unit/sampling/test_tiered_exercise_selection.py`
- `packages/database/tests/unit/database/test_tiered_transition.py`
- `packages/database_cache/tests/unit/database_cache/test_tiered_transition.py`

### Relevant Skills

- `feature-request`

## Work Items

### 1. Introduce one shared pure tiered logic module in `core`

Create `packages/core/src/nl_processing/core/repeat_state.py` with:

- pure repeat-state transition function
- pure repeat-state integrity validation
- pure tiered progress aggregation

The shared implementation must cover the current documented tiered semantics from `database` and `database_cache` docs.

### 2. Remove duplicated tiered state-machine logic from `database` and `database_cache`

Replace the local copies of transition logic and progress aggregation with imports from the shared `core` pure module.

Do not keep two independent implementations after this task.

### 3. Clean up `sampling`

Split `packages/sampling/src/nl_processing/sampling/service.py` into smaller files such as:

- `providers.py`
- `weights.py`
- `tiered_policy.py`
- `random_choice.py`
- `service.py`

Specific fixes required:

- correct the tiered sampler return annotation to match the documented contract;
- keep the public contract as `WordPair` return only;
- remove or isolate broken non-contract logic from the supported path;
- keep provider dependency structural and database-agnostic.

### 4. Update tests to one shared tiered transition matrix

The shared transition matrix must become the single source of truth used by:

- `core` unit tests
- `database` tiered tests
- `database_cache` tiered tests

The remote and cache paths must prove they use the same logic, not merely similar logic.

## Expected Files To Change

- `packages/core/src/nl_processing/core/repeat_state.py`
- `packages/core/tests/unit/core/`
- `packages/database/src/nl_processing/database/_tiered_helpers.py`
- `packages/database/src/nl_processing/database/_tiered_backend_ops.py`
- `packages/database/src/nl_processing/database/tiered_progress.py`
- `packages/database/tests/unit/database/test_tiered_transition.py`
- `packages/database_cache/src/nl_processing/database_cache/_tiered_helpers.py`
- `packages/database_cache/src/nl_processing/database_cache/_tiered_result_recorder.py`
- `packages/database_cache/src/nl_processing/database_cache/tiered_cache.py`
- `packages/database_cache/tests/unit/database_cache/test_tiered_transition.py`
- `packages/sampling/src/nl_processing/sampling/`
- `packages/sampling/tests/unit/sampling/`

## Acceptance Criteria

- exactly one shared pure implementation defines tiered repeat-state transitions;
- `database` tiered code uses the shared pure implementation;
- `database_cache` tiered code uses the shared pure implementation;
- `sampling` remains persistence-agnostic and depends only on shared provider contracts and shared models from `core`;
- `TieredMultiExerciseSampler.sample()` public contract matches docs and tests;
- no supported sampling path references uninitialized internal state;
- `packages/core`, `packages/database`, `packages/database_cache`, and `packages/sampling` checks are green.

## Verification

Run:

```bash
cd packages/core && make check
cd packages/database && make check
cd packages/database_cache && make check
cd packages/sampling && make check
```

Add explicit parity tests proving the remote and cache tiered paths produce the same next repeat-state for the same inputs.
