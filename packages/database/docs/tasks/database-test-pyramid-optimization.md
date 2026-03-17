---
title: "packages/database test-pyramid optimization"
document_type: "task"
module: "packages/database"
status: "todo"
---

# Task: Rebalance `packages/database` tests toward the intended test pyramid

## Problem Statement

`packages/database` is currently green, but its test ownership is still inverted relative to the target-state testing policy documented in `packages/database/docs/module-spec.md`.

The expensive e2e layer still owns too many DB-only behaviors:

- `get_words()` query/read behavior
- delete behavior
- `ExerciseProgressStore` persistence/snapshot behavior
- `DetailedWordStore` workflows using a fake extractor
- translated/untranslated read behavior that can be proven with seeded DB state

At the same time, the real-Neon integration layer is too narrow and is currently mostly detailed-store focused. This makes `make check` slower and noisier than necessary because `packages/database/Makefile` runs unit + integration + e2e on every full package check.

This task must optimize the test pyramid inside `packages/database` only, keep docs synchronized with the new ownership split, and adapt strictly to the current supported module contract. Do **not** restore or re-test removed APIs such as `DatabaseService.list_personal_words()` or `ExerciseProgressStore.get_progress_summary()`.

## Required Outcome

Rebalance the package so that:

- **Unit** keeps pure business-rule and mock-backend coverage.
- **Integration** owns DB semantics against real Neon without external translation calls.
- **E2E** keeps only one true smoke path for real OpenAI + Neon translation orchestration around `DatabaseService.add_words()` and eventual translated reads.

The optimization must come from shrinking the e2e layer to that single smoke scenario while keeping `packages/database/Makefile` semantics intact. `make test` and `make check` must still include unit + integration + e2e exactly as they do now. Do **not** remove e2e from the default flow unless the user explicitly requests that as a separate task.

## What Stays In Unit

Unit remains the home for pure business-rule and mock-backend coverage, including:

- `add_words()` deduplication and translator-trigger orchestration decisions
- `get_words()` warning/logging behavior that depends on mock counts rather than real SQL semantics
- delete validation and corpus-preservation behavior that does not require real Neon
- `ExerciseProgressStore` input validation (`exercise_type`, `delta`) and mock-backed score logic
- `DetailedWordStore` validation, extractor-calling behavior, payload parsing/validation, and other pure non-Neon control flow

Do not move existing valuable unit coverage into integration just because a similar integration test will exist; the target state is a balanced pyramid, not an integration-only test strategy.

## Relevant Context To Read First

### Canonical docs

- `README.md`
- `docs/module-spec.md`
- `packages/database/docs/module-spec.md`
- `packages/database/docs/tasks/baseline-repair-green-check.md`
- `packages/database/docs/tasks/database-progress-contract-cleanup.md`

### Package files directly relevant to this task

- `packages/database/Makefile`
- `packages/database/src/nl_processing/database/service.py`
- `packages/database/src/nl_processing/database/_service_helpers.py`
- `packages/database/src/nl_processing/database/exercise_progress.py`
- `packages/database/src/nl_processing/database/detailed_store.py`
- `packages/database/src/nl_processing/database/_user_operations.py`
- `packages/database/src/nl_processing/database/testing.py`
- `packages/database/tests/e2e/database/conftest.py`
- `packages/database/tests/e2e/database/test_word_addition_flow.py`
- `packages/database/tests/e2e/database/test_user_word_lists.py`
- `packages/database/tests/e2e/database/test_untranslated_words.py`
- `packages/database/tests/e2e/database/test_delete.py`
- `packages/database/tests/e2e/database/test_exercise_progress.py`
- `packages/database/tests/e2e/database/test_detailed_full_flow.py`
- `packages/database/tests/integration/database/conftest.py`
- `packages/database/tests/integration/database/test_detailed_integration.py`
- `packages/database/tests/unit/database/test_service.py`
- `packages/database/tests/unit/database/test_delete.py`
- `packages/database/tests/unit/database/test_exercise_progress.py`
- `packages/database/tests/unit/database/test_detailed_store_extract.py`
- `packages/database/tests/unit/database/conftest.py`
- `packages/database/tests/unit/database/mock_backend.py`

## Relevant Skills

- No specialized implementation skill is required for the core refactor.
- `set-up-env-vars` is only relevant if execution is blocked by missing/invalid Doppler-managed credentials for Neon or OpenAI. Do **not** broaden this task into env-var changes unless the user explicitly requests that work.
- Do not expand this task into cross-module spec work or unrelated feature planning.

## Dependencies

### Contract dependencies

- `packages/database/docs/module-spec.md` is the source of truth for the supported contract and testing policy.
- The current supported public contract includes `DatabaseService.add_words()`, `get_words()`, `delete_word()`, `delete_words()`, `create_tables()`, `ExerciseProgressStore`, and `DetailedWordStore`.
- Removed APIs `list_personal_words()` and `get_progress_summary()` are intentionally out of contract and must stay removed.

### Runtime and tooling dependencies

- `packages/database/Makefile` defines `make check` as `lint` + `test`, where `test` runs unit, integration, and e2e.
- Integration and e2e rely on real Neon under `doppler run`.
- E2E translation orchestration currently composes `DatabaseService` with `translate_word.WordTranslator`.

## Pre-Implementation Research Results

These findings are already established from repo inspection and should drive implementation directly.

1. `packages/database/docs/module-spec.md` already documents the intended split:
   - integration owns DB semantics without external translation
   - e2e is only for minimal real OpenAI + real Neon orchestration smoke
2. The current integration suite is too narrow: it contains only `tests/integration/database/test_detailed_integration.py`.
3. The current e2e suite is still broad:
   - `test_word_addition_flow.py`
   - `test_user_word_lists.py`
   - `test_untranslated_words.py`
   - `test_delete.py`
   - `test_exercise_progress.py`
   - `test_detailed_full_flow.py`
4. `tests/e2e/database/conftest.py` builds `DatabaseService(..., translator=WordTranslator(...))`; many e2e tests then wait for background translations via `cleanup_service(service)` even when the behavior under test is actually DB-only.
5. `service.py` delegates translated reads to `_service_helpers.get_words_impl()`, which proves that most `get_words()` behaviors are backend/query semantics, not OpenAI orchestration semantics.
6. `exercise_progress.py` implements `increment()`, `get_word_pairs_with_scores()`, `export_remote_snapshot()`, and `apply_score_delta(...)` entirely as DB-backed behavior over translated rows and score tables. These are integration responsibilities.
7. `detailed_store.py` uses an injected extractor. Existing broad e2e coverage uses a fake extractor, so those workflows are not true external end-to-end tests and should live in integration.
8. `test_delete.py` already manually seeds translated target rows and translation links after `add_words()`. That is strong evidence that translator-backed setup is unnecessary for delete coverage.
9. `packages/database/src/nl_processing/database/testing.py` already contains package-local reset/count helpers, but integration currently lacks reusable seed helpers for source rows, target rows, translation links, user membership, detail rows, and score rows.
10. `packages/database/docs/tasks/baseline-repair-green-check.md` is marked `done` but still contains active-looking broad e2e references; if those references now contradict the target test split, package docs must be trimmed or marked superseded.

## API / Library Research Needed For Implementation

Implementation will rely on standard pytest fixture patterns for reusable seeded scenarios.

### Pytest fixture factory pattern

Use fixtures that return helper callables so tests can create explicit seeded states without shared mutable cross-test state.

```python
@pytest.fixture
def make_seed(neon_backend):
    async def _make_seed(...):
        ...
    return _make_seed
```

Why this matters here:

- integration tests need broad seeded scenarios
- tests should reuse setup code without introducing module-global shared DB state
- pytest fixtures are explicitly designed to request other fixtures and return reusable objects/factories

Source: pytest docs, “How to use fixtures” and “Factories as fixtures”  
https://docs.pytest.org/en/stable/how-to/fixtures.html

### Async fixture pattern with `pytest_asyncio.fixture`

Async fixtures may be regular async fixtures or async generator fixtures:

```python
@pytest_asyncio.fixture
async def neon_backend(...):
    yield backend
```

`pytest_asyncio.fixture` also supports `loop_scope=...` when fixture/event-loop lifetime must be coordinated.

Source: pytest-asyncio reference, “Decorators”  
https://pytest-asyncio.readthedocs.io/en/stable/reference/decorators/

### Decision for this task

- Prefer package-local fixture factories and seed helpers for integration.
- Do not introduce shared mutable state across tests to save cost.
- Keep current schema reset discipline; reduce cost by seeding broader scenarios per test through helpers, not by reusing dirty state.

## Integration Seed-Helper Contract

Use a **separate helper module by default** for integration seeding:

- helper functions live in `packages/database/tests/integration/database/seed_helpers.py`
- `packages/database/tests/integration/database/conftest.py` stays thin and only exposes fixtures/factory fixtures that wrap those helpers

This is the default, not an optional preference. It matches the repo file-size rule and avoids turning `conftest.py` into an oversized mixed fixture + data-builder file.

### Required helper style

- Implement plain async helper functions in `seed_helpers.py`.
- Expose them to tests through small fixture factories from `conftest.py`, for example `make_seeded_word_pair`, `make_seeded_word_set`, or equivalent clearly named factories.
- Keep helper naming scenario-oriented rather than generic/opaque.
- Return the seeded IDs and canonical forms needed by tests so tests do not have to rediscover rows through extra exploratory queries.

### Minimum helper responsibilities

The helper layer must provide reusable building blocks that can directly seed all DB state needed by the new integration suite:

1. create canonical source word rows
2. create canonical target word rows
3. create translation links
4. create `user_words` membership rows
5. create score rows for one or more exercise types
6. create detailed-word rows with `schema_key`, `schema_version`, and payload
7. support multi-row seeding for one user in a single call so one integration test can cheaply create a richer scenario
8. return a structured result per seeded pair containing at least:
   - `source_word_id`
   - `target_word_id` when a translation row is created
   - `user_id`
   - source/target normalized forms
   - source `word_type`

### Required concrete helper surface

The implementation should expose fixture factories around helper functions with responsibilities equivalent to:

- `make_seeded_word_pair(...)` — create one user-visible translated or untranslated source row set and return its IDs
- `make_seeded_word_set(...)` — create several rows for one user with mixed `word_type` / translated-state scenarios in one call
- `seed_scores(...)` — attach one or more exercise scores to seeded source-word IDs
- `seed_detail_row(...)` — persist one detailed-word row for a canonical source word

Exact names may vary slightly, but this four-part responsibility split is required so the implementer does not invent an incompatible seeding model.

## Integration Isolation Strategy

Keep the integration suite cheap **without** hidden coupling between tests.

Required strategy:

- keep schema lifecycle package-local and explicit
- do not share mutable seeded data between tests
- every integration test must create its own isolated namespace using unique `user_id` values and unique word forms (for example UUID-suffixed forms)
- tests must assert against the rows they seeded, not against global table counts or assumptions that the database is otherwise empty
- seed helpers must return the exact IDs/forms needed for assertions so tests stay scoped to their own data
- no integration test may depend on data written by another test
- no module-scoped fixture may cache seeded domain rows for reuse across tests

This is the required cheaper model: shared schema bootstrap is acceptable, shared mutable test data is not.

## Explicit Target-State Decisions

1. Keep exactly **one** real e2e smoke scenario, meaning **one active e2e test function** in the package e2e suite. It may live in its own file with supporting fixtures/helpers, but only one e2e test function may remain responsible for real OpenAI + real Neon translation orchestration.
2. Move all DB-only `get_words()` coverage to integration with real Neon and direct seeded translations:
   - `word_type`
   - `limit`
   - `random`
   - user isolation
   - translated-only reads / untranslated exclusion
3. Move delete coverage to integration with real Neon and direct seeded rows, including score cleanup behavior.
4. Move `ExerciseProgressStore` coverage to integration with real Neon and no external translation calls, including:
   - `increment()`
   - default zero scores
   - cross-instance persistence
   - `export_remote_snapshot()` canonical snapshot behavior
   - `apply_score_delta(...)` idempotent replay where relevant
5. Move `DetailedWordStore` fake-extractor workflows from e2e to integration.
6. Add package-local integration seed helpers that directly create:
   - source word rows
   - target word rows
   - translation links
   - user membership rows
   - score rows
   - detailed rows where needed
7. When a test already seeds translations directly, do not use translator-backed setup or `cleanup_service()` in that test.
8. Do not restore, recreate, or newly test removed APIs: `list_personal_words()` and `get_progress_summary()` remain unsupported.
9. Preserve package-local schema setup/reset discipline. Optimization must come from the pyramid rebalance and reusable seed helpers, not from shared cross-test mutable DB state.
10. Keep docs synchronized with the final testing policy. If older task docs still present the old e2e-heavy split as active guidance, add a short superseded note or trim the conflicting references.
11. Keep `make test` / `make check` semantics unchanged; the optimization is reduced e2e breadth, not removal of e2e from CI/package checks.

## Scope

### In Scope

- Rebalance unit/integration/e2e ownership inside `packages/database`.
- Introduce reusable integration seed helpers for DB-backed scenarios.
- Rewrite or move tests so DB-only behavior is validated in integration.
- Reduce e2e to a single orchestration smoke scenario.
- Update package-local docs so the active testing policy matches the implemented split.
- Finish with full `make check` in `packages/database` 100% green.

### Out of Scope

- Any change outside `packages/database`.
- Restoring removed APIs or DTOs.
- Broad source-contract redesign.
- Changing external service configuration, credentials, or other module behavior.
- Weakening tests, skipping coverage, or changing `Makefile` gates to mask cost.

## File-Scope Expectations

Implementation must remain inside `packages/database`.

### Expected test files to change

- `packages/database/tests/integration/database/conftest.py`
- `packages/database/tests/integration/database/seed_helpers.py` (new)
- `packages/database/tests/integration/database/test_detailed_integration.py`
- `packages/database/tests/e2e/database/conftest.py`
- `packages/database/tests/e2e/database/test_word_addition_flow.py`
- `packages/database/tests/e2e/database/test_user_word_lists.py`
- `packages/database/tests/e2e/database/test_untranslated_words.py`
- `packages/database/tests/e2e/database/test_delete.py`
- `packages/database/tests/e2e/database/test_exercise_progress.py`
- `packages/database/tests/e2e/database/test_detailed_full_flow.py`

### Expected additional package-local files that may need updates

- `packages/database/tests/unit/database/test_service.py`
- `packages/database/tests/unit/database/test_delete.py`
- `packages/database/tests/unit/database/test_exercise_progress.py`
- `packages/database/tests/unit/database/conftest.py`
- `packages/database/tests/unit/database/mock_backend.py`
- `packages/database/src/nl_processing/database/testing.py`

### Expected docs to update inside package scope

- `packages/database/docs/module-spec.md`
- `packages/database/docs/tasks/baseline-repair-green-check.md`

### File-structure rule

- Keep `tests/integration/database/conftest.py` focused on fixture wiring and thin factory exposure only.
- Put integration seeding logic in `tests/integration/database/seed_helpers.py` by default.
- If `seed_helpers.py` approaches the repo line-count limit, split it into scenario-focused helper modules under `tests/integration/database/` rather than pushing logic back into `conftest.py`.
- If implementation appears to require edits outside `packages/database`, stop and escalate instead of crossing module boundaries.

## E2E Migration Matrix

Use this matrix as the required migration target for the current e2e suite.

| Current file | Target action | Required end state |
| --- | --- | --- |
| `packages/database/tests/e2e/database/test_word_addition_flow.py` | **Keep and trim** | This becomes the single e2e smoke owner. Leave exactly one active test function proving real translator orchestration from `add_words()` to eventual translated `get_words()` reads. Remove DB-only assertions that belong in lower layers. |
| `packages/database/tests/e2e/database/test_user_word_lists.py` | **Move coverage to integration, then remove or empty as e2e owner** | `get_words()` filter/limit/random/user-isolation behavior must live in integration. This file must no longer contain active e2e coverage for those behaviors. |
| `packages/database/tests/e2e/database/test_untranslated_words.py` | **Move coverage to integration, then remove or empty as e2e owner** | translated-only / untranslated-exclusion behavior must live in integration. This file must no longer contain active e2e coverage for those behaviors. |
| `packages/database/tests/e2e/database/test_delete.py` | **Move coverage to integration, then remove or empty as e2e owner** | delete behavior and score cleanup must live in integration. This file must no longer contain active e2e delete coverage. |
| `packages/database/tests/e2e/database/test_exercise_progress.py` | **Move coverage to integration, then remove or empty as e2e owner** | progress/snapshot/replay behavior must live in integration. This file must no longer contain active e2e progress coverage. |
| `packages/database/tests/e2e/database/test_detailed_full_flow.py` | **Move fake-extractor workflows to integration, then remove or empty as e2e owner** | detailed-store fake-extractor coverage must live in integration. This file must no longer contain active e2e detailed-store coverage. |

Removing or rewriting a file is acceptable; keeping DB-only tests in e2e is not.

## Implementation Plan

1. Reconfirm the target state against `packages/database/docs/module-spec.md` before editing tests so the refactor follows the already-documented policy instead of inventing a new split.
2. Design one package-local integration seeding API for real Neon tests. The helpers must create canonical DB state directly through backend operations instead of routing through translator-backed `DatabaseService.add_words()` for cases that do not need translation orchestration.
3. Create `packages/database/tests/integration/database/seed_helpers.py` and keep `tests/integration/database/conftest.py` thin. Implement fixture factories in `conftest.py` that wrap the helper functions from `seed_helpers.py`.
4. Add reusable helpers/fixtures for these seeded scenarios:
   - translated word pair for one user
   - multiple translated pairs with mixed `word_type`
   - same canonical corpus word linked to multiple users where needed
   - word pairs plus exercise-score rows
   - canonical source rows plus detailed rows
5. Ensure the integration helpers enforce per-test isolation by requiring explicit unique `user_id` and source/target forms from each test or by generating UUID-scoped defaults inside the helper. Tests must assert only against their own returned IDs/forms.
6. Expand the integration suite so it owns `DatabaseService.get_words()` DB semantics with real Neon and no external translation API:
   - translated-only reads
   - exclusion of untranslated rows
   - user isolation
   - `word_type` filtering
   - `limit`
   - `random`
7. Move delete coverage into integration using seeded rows and score rows. Verify both single-item and bulk delete behavior, plus explicit failure for deleting a word not in the user vocabulary.
8. Move `ExerciseProgressStore` persistence coverage into integration using seeded translated rows. Cover:
   - `increment()` score updates
   - default zero scores
   - cross-instance persistence
   - canonical snapshot export shape and contents
   - idempotent replay for `apply_score_delta(...)`
9. Move `DetailedWordStore` fake-extractor workflows from e2e into integration. Reuse the existing fake-extractor scenarios from `test_detailed_full_flow.py`, but seed canonical source rows directly and keep the DB real.
10. Trim the e2e layer down to one smoke scenario only. Preferred direction: keep or rewrite `test_word_addition_flow.py` so one scenario proves:
    - `DatabaseService.add_words()` with real `WordTranslator`
    - background translations complete through the package-owned cleanup path
    - `DatabaseService.get_words()` eventually returns translated pairs for the same user
    Do not keep filter/delete/progress/detailed-store responsibilities in e2e.
11. Delete or rewrite the remaining e2e files so they no longer preserve DB-only behavior in the e2e layer.
12. Keep `packages/database/Makefile` unchanged unless the user separately requests Makefile/CI surgery. The value comes from faster suites under the existing commands, not from redefining those commands.
13. Remove translator-backed setup from any test that directly seeds target rows and translation links.
14. Update package docs to describe the new active testing policy. At minimum:
    - keep `packages/database/docs/module-spec.md` aligned with the implemented suite ownership
    - update `packages/database/docs/tasks/baseline-repair-green-check.md` so it clearly reads as historical prerequisite work rather than current test-layer guidance
    - specifically: keep its `done` status, add a short superseded note near the top that active test-pyramid policy now lives in the newer task/module spec, and trim any lines that otherwise read like present-tense guidance for broad e2e ownership
15. Run targeted package-local test layers while editing, then finish with full `make check` in `packages/database`.

## Required Decision Rules During Implementation

- Treat the module spec as authoritative.
- Prefer direct DB seeding for integration over translator-backed setup unless the purpose of the test is translation orchestration itself.
- Keep one true e2e smoke test function only.
- Do not reintroduce removed APIs or rebuild old coverage around them.
- Reuse existing package helpers and backend methods where possible; do not add unnecessary alternate seeding paths.
- Do not change `Makefile` / default test-command semantics in this task.
- Preserve fail-fast behavior; do not add sleeps, retries, or weakened assertions just to make expensive tests pass.

## Acceptance Criteria

- E2E contains exactly one active real OpenAI + real Neon smoke **test function** centered on `DatabaseService.add_words()` and eventual translated reads.
- `get_words()` query/read behavior (`word_type`, `limit`, `random`, user isolation, translated-only reads) is covered in integration, not e2e.
- Delete behavior and score cleanup are covered in integration, not e2e.
- `ExerciseProgressStore` persistence/snapshot behavior is covered in integration, not e2e.
- `DetailedWordStore` fake-extractor workflows are covered in integration, not e2e.
- Integration tests reuse package-local seed helpers from `tests/integration/database/seed_helpers.py`, exposed through thin fixture factories in `conftest.py`.
- The integration helper layer provides the required seeding responsibilities for source rows, target rows, translation links, membership rows, score rows, and detailed rows.
- Integration tests stay isolated through unique per-test user/data namespaces and do not rely on shared mutable seeded state.
- Tests that seed translations directly no longer depend on translator-backed setup.
- No source or test changes restore or newly depend on `list_personal_words()` or `get_progress_summary()`.
- `packages/database/Makefile` still includes e2e in the default `make test` / `make check` flow.
- Package-local docs no longer present the old e2e-heavy split as current active policy.
- Full `make check` in `packages/database` is 100% green.

## Validation Gates

### Required targeted verification before final gate

- Run the relevant unit tests affected by any helper/test refactors.
- Run the full integration suite in `packages/database/tests/integration/database`.
- Run the remaining e2e smoke suite in `packages/database/tests/e2e/database`.
- Verify that only one active e2e test function still requires real translation orchestration.
- Verify that `make test` / `make check` semantics were not changed.
- Verify package-local docs reflect the implemented split.

### Mandatory final gate

- Run `make check` from `packages/database` and require 100% green completion.

### Quality expectations

- All linters, dead-code checks, duplication checks, and tests invoked by `make check` must be green unless a blocker below is hit and escalated.
- Follow existing package code style and the repo file-size rule; decompose rather than compact if helper growth pushes a file toward the line-count limit.

## Risks

- Integration helper design may accidentally become another opaque abstraction. Keep helpers explicit and scenario-focused.
- Broad test moves may uncover existing assumptions in fixtures that currently rely on translation side effects.
- There is a risk of under-testing the e2e smoke if too much is removed without replacing DB-semantics coverage in integration first.
- Historical task docs may continue to mislead developers if not explicitly trimmed or marked superseded.
- A tempting but wrong shortcut is to speed up checks by redefining `make test` or removing e2e from default package gates; that is out of scope and would hide, not solve, the pyramid issue.

## Blockers / Escalation Conditions

- If implementation requires touching any file outside `packages/database`, stop and escalate.
- If `packages/database/docs/module-spec.md` and the requested target state cannot be reconciled, stop and report the contradiction before editing tests.
- If the only way to keep `make check` green is to skip tests, reduce assertions, or weaken layer ownership, stop and escalate.
- If the only apparent optimization is changing `Makefile` / CI semantics rather than shrinking e2e ownership, stop and escalate because that is explicitly out of scope here.
- If missing Neon/OpenAI credentials or other Doppler configuration is the real blocker, stop and report it rather than silently expanding scope into env work.

## Done Definition

This task is done only when `packages/database` has a cheaper, properly layered test pyramid: one true e2e translation-orchestration smoke, broad real-Neon integration coverage for DB-only behavior, package-local docs synchronized to that policy, removed APIs still absent, and full `make check` 100% green.
