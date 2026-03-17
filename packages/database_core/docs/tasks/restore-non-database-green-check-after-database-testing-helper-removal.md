---
title: "Restore non-database green checks after database testing helper removal"
document_type: "task"
module: "packages/database_core"
status: "done"
---

# Task: Restore `packages/database_core` and `packages/database_cache` green checks without changing `packages/database`

## Problem Statement

The current baseline is broken in two non-database packages after upstream cleanup in `packages/database` removed previously available test-only helper exports from `nl_processing.database.testing`.

Validated current failures:

- `packages/database_core -> make check` fails during integration-test collection because `packages/database_core/tests/integration/database_core/test_table_creation.py` imports `count_words` from `nl_processing.database.testing`, but `packages/database/src/nl_processing/database/testing.py` no longer exports it.
- `packages/database_cache -> make check` fails during e2e-test collection because `packages/database_cache/tests/e2e/database_cache/conftest.py` imports `count_translation_links` from `nl_processing.database.testing`, but that helper is also no longer exported.

The user explicitly established that `packages/database` is already fixed and must remain read-only for this task. The repair must happen in downstream modules.

## Why This Task Exists

- `packages/database_core/docs/module-spec.md` explicitly says `database_core` sits below `database` and must stay unaware of the application-domain surface exposed by `database`.
- `database_core` acceptance criterion AC-3 requires backend-focused unit/integration tests to run from `database_core` without relying on `database` internals.
- `database_cache` is allowed to depend on supported public `database` behavior, but not on removed or undocumented helper exports.
- The previously completed `packages/database_cache/docs/tasks/baseline-repair-green-check.md` no longer describes the real target state because the upstream situation changed: `packages/database` is now green, and downstream packages must adapt.

## Relevant Context To Read First

### Repository and module docs

- `README.md`
- `docs/module-spec.md`
- `packages/database_core/docs/module-spec.md`
- `packages/database_cache/docs/module-spec.md`
- `packages/database/docs/module-spec.md`
- `packages/database_cache/docs/tasks/baseline-repair-green-check.md` (historical context only; do not treat it as the current source of truth)

### Files directly involved in the known failure surface

- `packages/database_core/tests/integration/database_core/test_table_creation.py`
- `packages/database_cache/tests/e2e/database_cache/conftest.py`
- `packages/database/src/nl_processing/database/testing.py` (read-only reference for what is still supported there)
- `packages/database_core/src/nl_processing/database_core/backend/abstract.py`
- `packages/database_core/src/nl_processing/database_core/backend/neon.py`
- `packages/database_cache/src/nl_processing/database_cache/service.py`
- `packages/database_cache/src/nl_processing/database_cache/sync.py`
- `packages/database_cache/Makefile`
- `packages/database_core/Makefile`

## Established Repo Facts

These are already validated and should be treated as fixed planning inputs:

- `git diff -- docs/` is empty.
- `packages/database -> make check` passes.
- `packages/database/src/nl_processing/database/testing.py` currently exports only:
  - `drop_all_tables(...)`
  - `reset_database(...)`
  - `count_user_words(...)`
- Current broken imports were found only in:
  - `packages/database_core/tests/integration/database_core/test_table_creation.py`
  - `packages/database_cache/tests/e2e/database_cache/conftest.py`
- `packages/database_core/Makefile` still sets `PYTHONPATH := src:../core/src:../database/src`, so the current test layout can import `database`, but architectural policy says `database_core` tests must not rely on `database` internals.
- `packages/database_cache/Makefile` runs `lint`, `test-unit`, `test-integration`, and `test-e2e` via `make check`; success means the full package gate is green.

## Relevant Skills

- No specialized implementation skill is required.
- Do **not** use `feature-request`, `bug-report`, or broader refactor/spec-rewrite workflows for this task.
- `set-up-env-vars` is **not** in scope. If implementation fails because Doppler/Neon credentials are invalid rather than because of package code/tests, stop and escalate instead of changing env setup here.

## Scope

### In Scope

- Restore green `make check` in `packages/database_core`.
- Restore green `make check` in `packages/database_cache`.
- Remove the architectural violation where `database_core` tests depend on `nl_processing.database.testing`.
- Adapt `database_cache` tests to the currently supported `database` surface or to package-owned test helpers, without expecting removed `database.testing` exports.
- Add or refactor package-local test support code in `packages/database_core` and `packages/database_cache` as needed.
- Keep all affected package checks, lint, and pytest layers green.

### Out of Scope

- Any modification to `packages/database` code, tests, docs, or exports.
- Any change to published/support contract of `packages/database`.
- Broad redesign of backend abstractions, cache architecture, or test infrastructure beyond what is needed to restore green gates.
- Root docs changes.
- Any workaround that weakens tests or quality gates.

## Architectural Direction That Must Be Preserved

### 1. `database_core` must stop depending on `database` test helpers

`database_core` is the lower-level backend package. Its docs say it must remain unaware of the application-domain surface exposed by `database`, and AC-3 explicitly requires backend-focused tests to run without relying on `database` internals. Therefore:

- importing `count_words` from `nl_processing.database.testing` inside `database_core` tests is architecturally wrong even if it were still available;
- the fix must move `database_core` test assertions onto `database_core`-owned APIs or `database_core`-owned test helpers;
- do not solve this by re-adding helpers to `packages/database`.

### 2. `database_cache` must adapt to the supported `database` surface

`database_cache` is allowed to use `database` as the canonical remote source of truth, but it must not require undocumented or removed helper exports. For this failure:

- do not restore `count_translation_links` in `packages/database`;
- instead, replace the e2e-only assertion mechanism with a package-local helper or another supported check owned by `database_cache` tests;
- keep the test focused on the real contract it needs: translations are available before cache-dependent e2e steps proceed.

## Expected File Scope For Implementation

### Primary files expected to change

#### `packages/database_core`

- `packages/database_core/tests/integration/database_core/test_table_creation.py`
- one or more new or existing package-local test helper files under `packages/database_core/tests/` if needed
- optionally, `packages/database_core/src/nl_processing/database_core/...` only if a small package-owned helper/API is truly needed for backend-level testability

#### `packages/database_cache`

- `packages/database_cache/tests/e2e/database_cache/conftest.py`
- one or more new or existing package-local test helper files under `packages/database_cache/tests/` if needed
- optionally, other existing `packages/database_cache/tests/e2e/...` files if small orchestration updates are needed after changing the waiting helper

### Files that must remain read-only

- all files under `packages/database/`
- all root docs and module specs
- unrelated packages

## Required Implementation Plan

### Part A — repair `packages/database_core`

1. Reproduce the current failure with the narrowest package-local command that reaches the broken import in `packages/database_core`.
2. Remove the import of `count_words` from `nl_processing.database.testing` in `packages/database_core/tests/integration/database_core/test_table_creation.py`.
3. Replace that assertion path with a `database_core`-owned mechanism.
   - Preferred direction: use `NeonBackend`/`AbstractBackend` capabilities already owned by `database_core` where possible.
   - The current backend already exposes `add_word(...)` and `count_user_words(...)`, but `count_user_words(...)` is user-membership-specific and is not equivalent to counting rows in `words_<lang>` tables. Do not substitute it incorrectly.
   - Introduce a small backend-level/package-local helper for counting canonical word rows in a language table if needed.
4. Keep the lifecycle test intent unchanged:
   - verify isolated table creation;
   - verify drop/reset behavior;
   - verify that inserted canonical word rows are present before reset and absent after reset.
5. Keep the repair local to `database_core` ownership. The test must no longer import anything from `nl_processing.database.testing`.

### Part B — repair `packages/database_cache`

1. Reproduce the current e2e collection failure with the narrowest package-local command that reaches the broken import in `packages/database_cache`.
2. Remove the import of `count_translation_links` from `nl_processing.database.testing` in `packages/database_cache/tests/e2e/database_cache/conftest.py`.
3. Replace `wait_for_translations(...)` with a package-local supported readiness check.
   - The readiness condition the e2e setup actually needs is: seeded words now have completed remote translations such that downstream cache flows can proceed.
   - Preferred direction: poll through a supported public service/API path rather than through a removed `database.testing` helper.
   - Keep the check aligned with documented behavior from `packages/database/docs/module-spec.md`: `DatabaseService.get_words()` returns only completed translation pairs.
4. Therefore, make the waiting helper assert translation readiness using a supported public `database` contract such as `DatabaseService.get_words()` for the seeded user until the expected number of translated pairs becomes visible.
5. Preserve the e2e test meaning:
   - seed words via real `DatabaseService.add_words(...)`;
   - wait until translations are truly available through supported reads;
   - only then initialize/use `DatabaseCacheService`.
6. Do not depend on private SQL shape or removed helper exports for this wait condition.

## Decision Rules

- Prefer package-owned helpers over reintroducing upstream compatibility shims.
- Reuse existing package APIs before adding new ones.
- If a new helper is needed, keep it narrowly scoped and owned by the affected package.
- Do not create a new cross-package dependency direction.
- Do not change docs as part of implementation unless the user separately requests docs changes; current docs already define the intended boundaries.
- Do not weaken tests, add sleeps as the main fix, skip tests, xfail failures, or relax linting.

## Implementation Notes / Chosen Technical Direction

### `database_core`

Use a `database_core`-owned counting path for `words_<lang>` table assertions.

Accepted options for implementation:

- add a narrow package-local integration-test helper under `packages/database_core/tests/...` that queries row count through the backend connection; or
- add a small backend-owned helper in `database_core` if that is the cleanest reusable location.

Preferred choice: a package-local test helper unless production code already has a natural backend-level counting primitive. This keeps production surface growth minimal while fully removing the dependency on `database`.

### `database_cache`

Use a supported public-API readiness check based on translated reads.

Concrete target behavior for the waiting helper:

- create/use the seeded user's `DatabaseService`;
- poll `get_words()` until the returned translated-pair count reaches `expected_count`;
- fail explicitly on timeout with observed count included.

This aligns the e2e seed wait with the documented contract instead of a removed test-only SQL helper.

## Validation Gates

The task is not done until all of the following are green:

- `packages/database_core -> make check`
- `packages/database_cache -> make check`

During diagnosis and repair, also run the narrowest commands needed to prove each fix:

- the `database_core` integration target that currently fails collection in `test_table_creation.py`
- the `database_cache` e2e target that currently fails collection via `tests/e2e/database_cache/conftest.py`

Final validation must confirm:

- no remaining import of `count_words` from `nl_processing.database.testing` in `packages/database_core`
- no remaining import of `count_translation_links` from `nl_processing.database.testing` in `packages/database_cache`
- linter/formatter/dead-code/duplication gates invoked by each package `make check` remain green
- all automated tests in both affected packages are green unless a documented external blocker is hit

## Acceptance Criteria

- AC-1: `packages/database_core/tests/integration/database_core/test_table_creation.py` no longer imports or depends on `nl_processing.database.testing`.
- AC-2: `database_core` backend-focused tests validate table lifecycle behavior using only `database_core`-owned APIs/helpers.
- AC-3: `packages/database_core -> make check` is fully green.
- AC-4: `packages/database_cache/tests/e2e/database_cache/conftest.py` no longer imports or depends on removed helper exports from `nl_processing.database.testing`.
- AC-5: `database_cache` e2e seeding waits for completed translations using a supported `database` contract rather than removed test-only helper exports.
- AC-6: `packages/database_cache -> make check` is fully green.
- AC-7: No files under `packages/database/` are modified.
- AC-8: Repo style rules are preserved, and all package-local automation in the affected packages remains green.

## Test Expectations

- Keep the current intent of the integration/e2e coverage intact.
- Only refactor tests/helpers as much as needed to align them with supported module boundaries.
- Add package-local regression protection if the new helper paths would otherwise be fragile.
- Ensure final verification covers formatter, lint, vulture, jscpd, and pytest layers through each package’s `make check`.

## Risks

- A seemingly small fix in `database_core` could tempt adding new production API surface when a package-local test helper would be enough.
- The `database_cache` e2e wait path may expose pre-existing translation timing flakiness once the import error is fixed.
- Additional downstream failures may appear after collection proceeds past the current broken imports.

## Blockers / Escalation Conditions

Stop immediately and report back instead of implementing across boundaries if any of the following becomes true:

- The only viable repair requires modifying any file under `packages/database/`.
- The supported public `database` contract is insufficient for `database_cache` e2e readiness checks and no package-local adaptation can solve it cleanly.
- `database_core` cannot validate its lifecycle behavior without growing a `database` dependency or introducing a misleading assertion based on the wrong semantic count.
- After fixing the import errors, `make check` in either affected package fails because of a separate contradiction between current code and module docs.
- Live integration/e2e failures prove the issue is purely environment readiness (for example broken Doppler/Neon credentials) rather than package code/tests.

## Done Definition

This task is done only when both non-database packages are green again, `database_core` no longer depends on `database` test helpers, `database_cache` no longer expects removed `database.testing` exports, and no changes were made to `packages/database`.
