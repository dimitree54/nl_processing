---
title: "packages/database duplicate progress-contract cleanup"
document_type: "task"
module: "packages/database"
status: "done"
---

# Task: Align `packages/database` with the cleaned progress contract

## Problem Statement

`packages/core` and `packages/database_cache` have already been cleaned up to remove duplicate progress-oriented public models and unsupported legacy progress contracts, but `packages/database` still exposes the old surfaces. The package is currently green because the prerequisite baseline-repair task is already complete, yet the public contract and package-local tests still preserve target-state drift.

This task removes the remaining duplicate progress-oriented DTOs and legacy convenience methods from `packages/database`, tightens the public API down to the target-state contract documented in `packages/database/docs/module-spec.md`, and updates package-local source/tests accordingly. This is a breaking cleanup by design. Do not add backward-compatibility shims.

## Baseline Status

- The prerequisite task in `packages/database/docs/tasks/baseline-repair-green-check.md` is already complete.
- `packages/database` is already green at baseline.
- That baseline repair is not part of this cleanup and must not be reopened here unless a new package-local regression is directly introduced by this cleanup.

## Required Context To Read First

### Specs and repo docs

- `README.md`
- `docs/module-spec.md`
- `packages/core/docs/module-spec.md`
- `packages/database/docs/module-spec.md`
- `packages/database_cache/docs/module-spec.md`
- `packages/database/docs/tasks/baseline-repair-green-check.md`

### Source files directly relevant to the cleanup

- `packages/core/src/nl_processing/core/models.py`
- `packages/database/src/nl_processing/database/models.py`
- `packages/database/src/nl_processing/database/service.py`
- `packages/database/src/nl_processing/database/exercise_progress.py`
- `packages/database/src/nl_processing/database/_user_operations.py`
- `packages/database/src/nl_processing/database/_progress_helpers.py`
- `packages/database/src/nl_processing/database/__init__.py`
- `packages/database/tests/unit/database/test_service.py`
- `packages/database/tests/unit/database/test_personal_vocab.py`
- `packages/database/tests/unit/database/test_progress_summary.py`
- `packages/database/tests/unit/database/test_exercise_progress.py`
- `packages/database/tests/integration/database/test_personal_vocab.py`
- `packages/database/tests/e2e/database/test_personal_vocab.py`
- `packages/database/tests/e2e/database/test_exercise_progress.py`

### Read-only cross-module context for contract alignment

- `packages/database_cache/src/nl_processing/database_cache/ports.py`

## Relevant Skills

- No specialized implementation skill is required for this cleanup.
- Treat the module specs as the source of truth instead of inventing policy.
- If implementation unexpectedly turns into env-var, DB bootstrap, or cross-module contract work, stop and escalate rather than loading unrelated skills and expanding scope.

## Scope

### In Scope

- Remove unsupported public DTOs from `packages/database` source and tests:
  - `PersonalWord`
  - `ExerciseProgressSummary`
  - `EnrichedWordPairSnapshot`
- Remove unsupported public methods from `packages/database` source and tests:
  - `DatabaseService.list_personal_words()`
  - `ExerciseProgressStore.get_progress_summary()`
- Make `ExerciseProgressStore.export_remote_snapshot()` return canonical `nl_processing.core.models.WordPairSnapshot`.
- Preserve `ExerciseProgressStore` as the supported remote score-bearing surface for:
  - `increment()`
  - `get_word_pairs_with_scores()`
  - `export_remote_snapshot()`
  - `apply_score_delta(...)`
- Preserve `DatabaseService` as the supported add/get/delete/create-table surface only.
- Keep `DetailedWordStore` behavior intact.
- Remove or update package-local helpers/tests that only exist for removed legacy surfaces.
- Finish with full `make check` in `packages/database` 100% green.

### Out of Scope

- Reopening the already-finished baseline-repair work.
- Any change outside `packages/database`.
- Any change to `packages/database/docs/module-spec.md`.
- Any compatibility layer, deprecation wrapper, alias class, or shim for removed DTOs/methods.
- Any redesign of `DetailedWordStore` or detailed-word persistence behavior.
- Any follow-up cleanup in `packages/core`, `packages/database_cache`, or downstream callers.

## Dependencies

### Contract dependencies

- `packages/database/docs/module-spec.md` is the target-state contract and wins over legacy package code/tests.
- `packages/core/docs/module-spec.md` and `packages/core/src/nl_processing/core/models.py` define the canonical shared progress/snapshot models to use.
- `packages/database_cache/docs/module-spec.md` and `packages/database_cache/src/nl_processing/database_cache/ports.py` confirm that the remote snapshot sync contract expects `core.WordPairSnapshot`.

### Runtime and tooling dependencies

- `packages/database/Makefile` defines the required quality gate: `make check`.
- `uv`, `doppler`, Ruff, pylint, vulture, jscpd, and pytest remain the package-local tooling path.
- The package is already green before starting; treat new failures as cleanup regressions unless they are proven pre-existing and unrelated.

## Pre-Implementation Research Results

These findings are already established from repo docs and current `packages/database` code. Treat them as fixed starting context for implementation.

- `packages/database/docs/module-spec.md` explicitly marks `PersonalWord`, `ExerciseProgressSummary`, `EnrichedWordPairSnapshot`, `list_personal_words()`, and `get_progress_summary()` as unsupported target-state surfaces.
- `packages/core/src/nl_processing/core/models.py` defines canonical `ScoredWordPair` and `WordPairSnapshot`; `WordPairSnapshot` already has the exact stable-ID-and-`added_at` shape needed by remote snapshot export.
- `packages/database_cache/src/nl_processing/database_cache/ports.py` already types `export_remote_snapshot()` as returning `list[WordPairSnapshot]`.
- `packages/database/src/nl_processing/database/models.py` still contains the three duplicate/legacy DTOs, while `AddWordsResult` remains valid and should stay.
- `packages/database/src/nl_processing/database/service.py` still exposes `list_personal_words()` and imports `PersonalWord` plus `list_personal_words_impl`.
- `packages/database/src/nl_processing/database/_user_operations.py` currently mixes supported delete behavior with unsupported personal-vocabulary read-model construction.
- `packages/database/src/nl_processing/database/exercise_progress.py` still exposes `get_progress_summary()` and constructs `EnrichedWordPairSnapshot` even though the canonical shared model already contains `source_word_id`, `target_word_id`, `scores`, and `added_at`.
- `packages/database/src/nl_processing/database/_progress_helpers.py` exists only to support the removed `get_progress_summary()` path; after the cleanup it should not remain as dead support code.
- Package-local tests still preserve removed behavior through dedicated legacy test files and snapshot type assertions against `EnrichedWordPairSnapshot`.
- The baseline-repair task already added background-translation cleanup helpers used by current e2e tests; this cleanup should reuse that repaired behavior, not redesign it.
- No external API or rapidly changing library research is required for this cleanup. The necessary contract references are all inside the repo.

## Explicit Target-State Decisions

1. `DatabaseService` supports only `add_words()`, `get_words()`, `delete_word()`, `delete_words()`, and `create_tables()` as public operational methods for this cleanup.
2. `DatabaseService.list_personal_words()` is removed outright from source and tests. Do not replace it with another package-local translated personal-vocabulary DTO surface.
3. `ExerciseProgressStore` keeps only the score-bearing remote surface documented in the module spec: `increment()`, `get_word_pairs_with_scores()`, `export_remote_snapshot()`, and `apply_score_delta(...)`.
4. `ExerciseProgressStore.get_progress_summary()` is removed outright from source and tests. Callers that need summaries must derive them outside `packages/database` from canonical snapshot or scored-pair data.
5. `ExerciseProgressStore.export_remote_snapshot()` returns `list[WordPairSnapshot]` from `nl_processing.core.models`, not a database-local subclass.
6. `packages/database/src/nl_processing/database/models.py` remains the home of `AddWordsResult` only unless another documented, still-supported package-local model is already required. The three removed DTOs must not remain there as dead code.
7. `_progress_helpers.py` is dead after this cleanup and should be deleted rather than kept as unreachable legacy support code.
8. `_user_operations.py` should keep supported delete helpers only; remove personal-vocabulary read-model code from it.
9. `DetailedWordStore`, detailed ports/models, and detailed-word tests stay behaviorally unchanged unless package-local cleanup is required only to keep checks green.
10. If implementation reveals that this cleanup cannot be completed without changing another module, stop immediately and escalate with the exact dependency instead of crossing the module boundary.

## File-Scope Expectations

Implementation must stay inside `packages/database`.

### Expected source files to change

- `packages/database/src/nl_processing/database/models.py`
- `packages/database/src/nl_processing/database/service.py`
- `packages/database/src/nl_processing/database/exercise_progress.py`
- `packages/database/src/nl_processing/database/_user_operations.py`

### Expected source files to delete if they become dead

- `packages/database/src/nl_processing/database/_progress_helpers.py`

### Expected test files to remove or rewrite

- `packages/database/tests/unit/database/test_personal_vocab.py`
- `packages/database/tests/unit/database/test_progress_summary.py`
- `packages/database/tests/integration/database/test_personal_vocab.py`
- `packages/database/tests/e2e/database/test_personal_vocab.py`
- `packages/database/tests/e2e/database/test_exercise_progress.py`
- `packages/database/tests/unit/database/test_exercise_progress.py`

### Additional package-local files that may need small updates

- `packages/database/tests/unit/database/conftest.py`
- `packages/database/tests/unit/database/test_service.py`

### File-scope rule

- Do not touch any file outside `packages/database`.
- If a required change appears to belong in another module, stop and escalate.

## Implementation Plan

1. Re-read `packages/database/docs/module-spec.md` together with `packages/core/src/nl_processing/core/models.py` and `packages/database_cache/src/nl_processing/database_cache/ports.py` immediately before editing so the cleanup stays pinned to the actual supported contract.
2. Remove the three unsupported DTO classes from `packages/database/src/nl_processing/database/models.py` and keep `AddWordsResult` intact.
3. Remove `DatabaseService.list_personal_words()` from `packages/database/src/nl_processing/database/service.py`, along with imports of `PersonalWord` and `list_personal_words_impl`.
4. Remove `list_personal_words_impl()` and its `PersonalWord` construction logic from `packages/database/src/nl_processing/database/_user_operations.py`, leaving supported delete behavior intact.
5. Remove `ExerciseProgressStore.get_progress_summary()` from `packages/database/src/nl_processing/database/exercise_progress.py`.
6. Update `ExerciseProgressStore.export_remote_snapshot()` so its signature, imports, local variable types, and constructed objects all use canonical `WordPairSnapshot` from `nl_processing.core.models`.
7. Delete `packages/database/src/nl_processing/database/_progress_helpers.py` because it only supports the removed summary API.
8. Remove or rewrite unit tests that directly depend on removed DTOs/methods:
   - delete legacy personal-vocabulary tests instead of rephrasing them around another unsupported surface
   - delete legacy progress-summary tests instead of preserving the behavior under a new name
   - update snapshot tests to assert canonical `WordPairSnapshot` rather than `EnrichedWordPairSnapshot`
9. Remove or rewrite integration/e2e tests that directly call removed APIs:
   - delete the dedicated `list_personal_words` integration/e2e tests
   - remove the `get_progress_summary` e2e coverage
   - keep score-bearing and snapshot-export e2e coverage focused on the supported contract
10. Tighten package-local tests around the supported contract that remains:
    - `export_remote_snapshot()` returns canonical `WordPairSnapshot`
    - exported snapshots still include stable IDs, `scores`, and `added_at`
    - `get_word_pairs_with_scores()` still returns `ScoredWordPair`
    - `DatabaseService` delete/add/get/create-table behavior remains intact
11. Run targeted package-local tests while editing, then run full `make check` in `packages/database` and fix any cleanup regressions without reintroducing removed surfaces.
12. Before finishing, perform an explicit package-local search to confirm the removed DTO and method names no longer appear in production code or active tests, except where historical mention inside this task file or other untouched docs is unavoidable.

## Required Implementation Rules

- Follow `packages/database/docs/module-spec.md` exactly; do not silently invent a replacement contract.
- Treat this as breaking cleanup. Do not leave aliases, wrapper methods, subclass-based compatibility, or deprecated placeholders.
- Reuse canonical shared models from `packages/core` instead of keeping package-local duplicates.
- Keep detailed-word code behavior intact.
- Prefer deletion over orphaned dead support code.
- If package-local code and the module spec still disagree after your changes, report the remaining spec drift instead of making undocumented contract changes.

## Acceptance Criteria

- `packages/database/src/nl_processing/database/models.py` no longer defines `PersonalWord`, `ExerciseProgressSummary`, or `EnrichedWordPairSnapshot`.
- `packages/database/src/nl_processing/database/service.py` no longer exposes `DatabaseService.list_personal_words()`.
- `packages/database/src/nl_processing/database/exercise_progress.py` no longer exposes `ExerciseProgressStore.get_progress_summary()`.
- `ExerciseProgressStore.export_remote_snapshot()` returns canonical `nl_processing.core.models.WordPairSnapshot` records with stable IDs, `scores`, and `added_at` intact.
- `ExerciseProgressStore` still supports `increment()`, `get_word_pairs_with_scores()`, `export_remote_snapshot()`, and `apply_score_delta(...)`.
- `DatabaseService` still supports add/get/delete/create-table workflows and no longer preserves a translated personal-vocabulary read-model surface.
- `DetailedWordStore` behavior and detailed-word persistence tests remain green.
- Package-local tests and helpers for removed DTOs/methods are deleted or rewritten so the unsupported surfaces are not preserved by test coverage.
- No backward-compatibility shim for any removed DTO or method remains in `packages/database` source.
- Full `make check` in `packages/database` completes successfully and is 100% green.

## Validation Gates

### Mandatory final gate

- Run `make check` from `packages/database` and require it to finish 100% green.

### Required targeted verification before the final gate

- Run targeted unit tests covering `ExerciseProgressStore` and `DatabaseService` after the cleanup edits.
- Run the relevant integration/e2e progress-store coverage that remains after deleting legacy tests.
- Run a package-local search for removed names in source and active tests, for example:
  - `rg "PersonalWord|ExerciseProgressSummary|EnrichedWordPairSnapshot|list_personal_words|get_progress_summary" packages/database/src packages/database/tests`
- Verify that the remaining `export_remote_snapshot()` assertions check `WordPairSnapshot`, not a database-local subclass.
- Verify that all linter, dead-code, duplication, and test gates invoked by `make check` are green.

## Risks

- Removing legacy tests may expose hidden assumptions in nearby fixtures or helpers that implicitly expected the old surfaces.
- `service.py` and `exercise_progress.py` are close to the repo file-size threshold; if cleanup plus small rewrites pushes a file over the limit, do a proper package-local decomposition instead of compacting logic.
- Downstream code outside `packages/database` may still rely on removed APIs even if package-local tests are updated. That follow-up is outside this task's scope and must be escalated, not patched here.
- Stale repo docs outside `packages/database` may continue mentioning old ownership or old contract shapes. Do not edit them in this task unless the user explicitly expands scope.

## Blockers / Escalation Conditions

- If implementing this cleanup requires modifying any module outside `packages/database`, stop and escalate with the exact file and reason.
- If `packages/database/docs/module-spec.md` conflicts with the requested cleanup in a way that prevents a single target state, stop and report the contradiction instead of inventing a hybrid contract.
- If `DetailedWordStore` or another still-supported surface unexpectedly depends on one of the removed DTOs/methods, stop and escalate before broadening the cleanup.
- If a failing check can only be fixed by restoring a removed legacy surface, stop and escalate; that means another package or test still depends on unsupported contract.
- If you discover remaining repo-level doc or caller drift outside `packages/database`, report it explicitly as follow-up work rather than editing other modules.

## Done Definition

This task is done only when `packages/database` matches the target-state cleanup already established in `packages/core` and `packages/database_cache`, all unsupported legacy DTOs/methods are removed from package source and tests, canonical `core.WordPairSnapshot` is the only snapshot export model used by `ExerciseProgressStore`, `DetailedWordStore` remains intact, and package-local `make check` is fully green.
