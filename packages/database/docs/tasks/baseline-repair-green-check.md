---
title: "packages/database baseline green-check repair"
document_type: "task"
module: "packages/database"
status: "done"
---

# Task: Restore `packages/database` baseline green state

## Problem Statement

`packages/database` is not currently at a clean baseline, but the next planned duplicate-model/progress-contract cleanup must start from a fully green package state. This prerequisite task exists to restore a 100% green `make check` in `packages/database` first and only then unblock the larger cleanup/refactor.

`packages/database/Makefile` defines `make check` as `lint` plus `test`, and `test` expands to `test-unit`, `test-integration`, and `test-e2e`. The currently established e2e failures are both tied to package-local async lifecycle and teardown behavior:

- `packages/database/tests/e2e/database/conftest.py::wait_for_translations()` can raise even when the final count already equals the expected value. Recent observed failure: `Translations did not complete within 15.0s (expected=4, actual=4)`.
- Background translation spawned by `DatabaseService.add_words()` can outlive test teardown and then hit a schema that has already been dropped/recreated, surfacing failures such as `relation "words_ru" does not exist` from `packages/database/src/nl_processing/database/_translation.py`.

This task is intentionally narrow. Do not start the larger duplicate-model/progress-contract cleanup here.

## Why This Exists

- The larger cleanup must begin from a known-green `packages/database` baseline.
- The current e2e failures blur the line between pre-existing async teardown defects and the upcoming architectural work.
- The failures point to package-owned lifecycle behavior around translation scheduling and test synchronization, so the package must first become deterministic under its own `make check` contract.

## Relevant Context To Read First

### Repo and module docs

- `README.md`
- `docs/module-spec.md`
- `packages/database/Makefile`
- `packages/database/docs/module-spec.md`
- `packages/database_core/docs/module-spec.md`

### Source and tests directly relevant to this repair

- `packages/database/src/nl_processing/database/service.py`
- `packages/database/src/nl_processing/database/_translation.py`
- `packages/database/src/nl_processing/database/testing.py`
- `packages/database/tests/e2e/database/conftest.py`
- `packages/database/tests/e2e/database/test_word_addition_flow.py`
- `packages/database/tests/e2e/database/test_user_word_lists.py`
- `packages/database/tests/e2e/database/test_untranslated_words.py`
- `packages/database/tests/e2e/database/test_personal_vocab.py`
- `packages/database/tests/e2e/database/test_exercise_progress.py`
- `packages/database/tests/e2e/database/test_delete.py`

### Read-only upstream/dependency context allowed for diagnosis

- Reading other modules for diagnosis is allowed.
- Modifying files outside `packages/database` is not allowed in this task.

- `packages/database_core/src/nl_processing/database_core/backend/neon.py`
- `packages/database/tests/integration/database/conftest.py`

## Pre-Implementation Research Results

These findings are already established from repo inspection and the observed failures. Treat them as starting context, not hypotheses to rediscover from scratch:

- `packages/database/Makefile` requires `lint`, `test-unit`, `test-integration`, and `test-e2e` through `make check`; completion means the whole package gate is green.
- `packages/database/src/nl_processing/database/service.py::add_words()` schedules translation with `asyncio.create_task(self._delayed_translation(...))` and returns immediately.
- `packages/database/src/nl_processing/database/service.py::_delayed_translation()` uses the injected backend only for `MockBackend`; for real runs it creates a fresh `NeonBackend(read_database_url())`.
- `packages/database/src/nl_processing/database/_translation.py::translate_and_store()` catches broad exceptions, logs a warning, and does not propagate the background failure back to the caller.
- `packages/database/tests/e2e/database/conftest.py::db_ready()` resets the database before each test, then drops tables and recreates them again during teardown while holding advisory lock `12345`.
- Because translation is fire-and-forget and untracked, package-owned background work can still be running while e2e teardown is dropping or recreating `words_*` and `translations_*` tables.
- `wait_for_translations()` currently polls once per second while `elapsed < timeout`, then performs one final count after the loop and raises immediately if the loop exited. That shape explains the false-negative `expected=4, actual=4`: the helper can miss a success reached just after the final sleep and still fail because it never re-checks success after the loop condition trips.
- The teardown/schema-race failure is package-local, not just a flaky external service symptom: the same package owns the background task creation, the lack of task tracking, and the teardown sequence that destroys the schema while detached translation work may still be executing.
- `packages/database/docs/module-spec.md` explicitly documents that `add_words()` optionally schedules background translation and that read APIs only surface completed translation pairs. This baseline repair must preserve those contracts while making the lifecycle deterministic enough for package checks.
- Docs other than this task file are out of scope for this prerequisite repair.

## Relevant Skills

- No specialized OpenCode implementation skill is required for this repair.
- Do not broaden this task into `feature-request`, `bug-report`, or `module-spec-agent`; this is a prerequisite baseline repair only.
- `set-up-env-vars` is not part of implementation. If the only reproduced issue is bad/missing Doppler or Neon configuration rather than package code/tests, stop and escalate instead of changing env setup in this task.

## Baseline-Repair Framing

- Treat the broader architectural assumptions documented in `packages/database/docs/module-spec.md` as fixed background for this baseline repair.
- Do not reopen duplicate-model ownership, progress-contract shape, or larger persistence-boundary questions here.
- The goal is to restore package health under the current documented module contract, not to redesign that contract.

## API / Library Research For The Expected Fix Direction

The chosen repair path relies on standard `asyncio` task ownership and cancellation semantics rather than ad hoc sleeps.

### Chosen implementation pattern

Use instance-level task tracking on `DatabaseService`:

- store created translation tasks on the service instance in a task set
- add a done-callback that removes completed tasks from that set
- add an explicit async service method that drains/awaits outstanding translation tasks owned by that service instance

This is the preferred pattern for this codebase because it fits the existing public service shape with the smallest package-local change:

- it preserves the current `DatabaseService.add_words()` contract, which already schedules background translation per service instance
- it keeps task ownership local to the object that created the work instead of introducing cross-instance global registries
- it avoids requiring a `TaskGroup`-oriented public call pattern around `add_words()` or broader structured-concurrency API changes across callers/tests
- it gives e2e fixtures a deterministic package-owned cleanup hook without changing module boundaries

Do not choose a global task registry or a new `TaskGroup`-driven public API for this baseline repair unless implementation proves the documented instance-level pattern is impossible inside package scope; if that happens, stop and escalate.

### Official `asyncio` guidance supporting this pattern

Python docs for `asyncio.create_task()` explicitly say to keep a strong reference to created tasks and show the standard pattern of storing background tasks in a collection plus removing them with `task.add_done_callback(background_tasks.discard)`.

```python
background_tasks = set()

task = asyncio.create_task(some_coro())
background_tasks.add(task)
task.add_done_callback(background_tasks.discard)
```

Python docs also state that task cancellation should use `try/finally` cleanup and should not swallow `CancelledError` incorrectly.

```python
task.cancel()
try:
    await task
finally:
    ...
```

`asyncio.TaskGroup` is the structured-concurrency alternative when related tasks must be awaited as a unit before shutdown/exit.

```python
async with asyncio.TaskGroup() as tg:
    tg.create_task(some_coro())
```

Sources:

- https://docs.python.org/3/library/asyncio-task.html#create_task
- https://docs.python.org/3/library/asyncio-task.html#task-cancellation
- https://docs.python.org/3/library/asyncio-task.html#task-groups

### Practical implication for this task

- Proper fixes should prefer explicit lifecycle/task management or deterministic test synchronization.
- Do not stabilize with extra `sleep(...)` calls as the main strategy.
- Do not treat timeout inflation as a fix unless root-cause evidence proves healthy completion simply exceeds the current bound.

## Wait Helper Fix Requirement

`wait_for_translations()` must be fixed directly even if the lifecycle repair makes translation completion more deterministic.

Required corrected logic:

1. Poll until timeout while checking `count_translation_links(...)` each iteration.
2. Return immediately on any iteration where `count >= expected_count`.
3. After the polling loop exits, perform one final count query.
4. If that final `actual >= expected_count`, return success.
5. Raise `AssertionError` only when the final observed `actual` still fails the expected condition.

Equivalent target logic:

```python
elapsed = 0.0
while elapsed < timeout:
    actual = await count_translation_links(table, backend=backend)
    if actual >= expected_count:
        return
    await asyncio.sleep(interval)
    elapsed += interval

actual = await count_translation_links(table, backend=backend)
if actual >= expected_count:
    return

raise AssertionError(
    f"Translations did not complete within {timeout}s "
    f"(expected={expected_count}, actual={actual})"
)
```

This fix is required regardless of any task-lifecycle repair because the current helper has an independent false-negative bug at the timeout boundary.

## Task Lifecycle Cleanup Requirement

The lifecycle/task-tracking repair is also required regardless of the wait-helper fix.

### Required ownership model

- Translation task references must live on each `DatabaseService` instance that created them.
- The service instance must be the owner responsible for draining its own outstanding background translation work.

### Required API shape

Implementation should add one explicit async cleanup method on `DatabaseService` dedicated to background translation ownership, for example `wait_for_background_translations()` or equivalently named drain method.

The method must:

- await all currently outstanding translation tasks owned by that service instance
- surface real task errors to the caller instead of silently swallowing them at cleanup time
- leave no owned translation task still running after it returns

An additional `close()`/`shutdown()` async wrapper may be added only if it improves package-local lifecycle clarity, but the minimum required API is an explicit async drain/wait method for translation tasks.

### Required cleanup behavior

- Preferred strategy is await-first: tests/fixtures should explicitly await the service-owned drain method before teardown begins dropping or recreating schema.
- If cancellation is needed during cleanup, it must still be explicit, awaited, and fail-fast on unexpected errors.
- Do not use sleep-based teardown.
- Do not silently suppress task failures during cleanup.
- Do not rely on garbage collection or weak task references to settle background work.

### Where tests/fixtures should use it

- Any e2e fixture or test path that creates a `DatabaseService` with background translation enabled must call the explicit service cleanup/drain method before fixture teardown starts schema drop/recreate work.
- If helper factories such as `make_service(...)` remain the common construction path, package-local e2e fixture strategy should make it straightforward for tests to drain the same service instances they created.

### Relationship between the two known fixes

- The `wait_for_translations()` logic repair is required regardless.
- The lifecycle/task-tracking repair is also required regardless.
- If the lifecycle repair makes waiting thinner or more deterministic, that is good, but both failure classes must still be directly fixed and covered.

## Scope

### In Scope

- Restore a fully green `make check` in `packages/database`.
- Properly fix the `wait_for_translations()` false-failure path.
- Properly fix the background-translation lifecycle/schema race so package-owned translation work cannot outlive package-owned teardown in a way that breaks e2e isolation.
- Add or adjust the minimum coherent package-local source/test coverage needed to keep the repaired behavior stable.
- Reproduce and resolve any additional package-local failures that are directly uncovered while returning the package to green.

### Out of Scope

- The larger duplicate-model/progress-contract cleanup or any broader architectural refactor.
- Changes outside `packages/database`.
- Any documentation updates other than this task file.
- Any edit to `packages/database/docs/module-spec.md`.
- Skipping, xfail-marking, quarantining, or weakening tests/checks to manufacture a green state.
- Fixes whose main mechanism is inflating timeouts, adding arbitrary sleeps, or weakening teardown/isolation guarantees.

## Dependencies

### Code and contract dependencies

- `packages/database/Makefile` is the package completion contract.
- `packages/database/docs/module-spec.md` is the behavioral background for `DatabaseService`, background translation, and translated-read semantics, but it must remain unchanged here.
- `packages/database_core` provides the backend implementation used by real package runs; it may be read for diagnosis but not modified.

### Runtime and tooling dependencies

- `uv` for package environment sync and command execution.
- `doppler run` for integration/e2e environment injection.
- Ruff, pylint, vulture, jscpd, and pytest as invoked by `make check`.
- Live Neon-backed integration/e2e execution through the existing package test setup.

## Explicit File Scope Expectations For Implementation

Implementation must stay inside `packages/database`.

Expected primary file scope:

- `packages/database/src/nl_processing/database/service.py`
- `packages/database/src/nl_processing/database/_translation.py`
- `packages/database/src/nl_processing/database/testing.py`
- `packages/database/tests/e2e/database/conftest.py`
- `packages/database/tests/e2e/database/test_word_addition_flow.py`
- `packages/database/tests/e2e/database/test_user_word_lists.py`
- `packages/database/tests/e2e/database/test_untranslated_words.py`
- `packages/database/tests/e2e/database/test_personal_vocab.py`
- `packages/database/tests/e2e/database/test_exercise_progress.py`
- `packages/database/tests/e2e/database/test_delete.py`

Implementation note:

- `packages/database/src/nl_processing/database/service.py` is already near the repo file-size limit. If the lifecycle repair would push it over the package rule, plan file decomposition/refactoring instead of compacting logic into the existing file.

Conditionally allowed only if directly required by reproduced package-local failures uncovered during repair:

- Other existing files under `packages/database/src/nl_processing/database/`
- Other existing files under `packages/database/tests/`
- Existing package-local config files under `packages/database/` only if an actual reproduced `make check` failure proves a package-local config defect

Not allowed:

- Any file outside `packages/database`
- Any docs other than this task file
- `packages/database/docs/module-spec.md`
- Changes whose only purpose is to skip or soften failing checks

## Implementation Plan

1. Reproduce the baseline by running `make check` in `packages/database`, then capture which gate fails first now.
2. Re-run the relevant e2e tests directly to confirm both currently known failure shapes:
   - the `wait_for_translations()` false-failure path
   - the background translation teardown/schema race
3. Repair `packages/database/tests/e2e/database/conftest.py::wait_for_translations()` so success is determined by an actual final condition check rather than by loop timing artifacts. The helper must not raise when the final observed count already satisfies the expectation.
4. Trace the lifecycle of background translation from `DatabaseService.add_words()` through `_delayed_translation()` and e2e teardown. Identify the package-owned place where task ownership must become explicit.
5. Implement a package-local lifecycle fix that makes translation work deterministic relative to teardown. Preferred direction:
   - keep strong references to package-owned translation tasks on each `DatabaseService` instance
   - add an explicit async `DatabaseService` drain/wait method for outstanding translation tasks
   - ensure any real-backend translation task completes or is cancelled before schema teardown begins
   - keep fail-fast behavior and do not hide real translation failures
   - keep the implementation package-local and avoid broader public API redesign
6. Add or tighten package-local regression coverage proving both repaired behaviors:
    - waiting helper no longer false-fails on the final successful count
    - package-owned translation tasks do not keep running against dropped/recreated tables during test teardown
7. Re-run targeted unit, integration, and e2e tests after each fix until the known failures are stable.
8. Finish by running full `make check` in `packages/database` and fix any additional package-local regressions uncovered on the way.

## Required Decision Rules During Implementation

- Treat this as a prerequisite baseline repair before the larger cleanup/refactor, not as the cleanup itself.
- Fix both known failure classes properly.
- Prefer explicit lifecycle management and deterministic synchronization over timing guesses.
- Preserve fail-fast behavior. Do not add silent fallbacks, hidden retries, or exception swallowing to manufacture green tests.
- Reading files in other modules for diagnosis is allowed; modifying files outside `packages/database` is not.
- If the only viable fix requires changing another module, stop and escalate with exact evidence instead of crossing the module boundary.

## Proper Fix vs Unacceptable Workaround

### Counts As A Proper Fix

- Making package-owned background translation tasks explicitly tracked and drained, awaited, or cancelled before teardown.
- Implementing instance-level translation-task tracking on `DatabaseService` with set-based ownership and done-callback cleanup.
- Adding an explicit async service drain/wait method that fixtures/tests call before schema teardown.
- Adding an explicit service/test synchronization mechanism for translation completion instead of relying on incidental event-loop timing.
- Correcting the wait helper logic so it checks the real completion condition at the timeout boundary.
- Adding regression coverage that proves package-owned async work no longer outlives package-owned schema reset/teardown.

### Does Not Count As A Proper Fix

- Increasing the `wait_for_translations()` timeout without root-cause evidence that the healthy deterministic path truly needs it.
- Adding `sleep(...)` in tests or teardown as the primary stabilization strategy.
- Skipping, xfail-marking, or quarantining failing tests.
- Weakening DB teardown/reset isolation so orphaned work becomes less visible.
- Leaving fire-and-forget tasks detached and merely suppressing their failures.

## Acceptance Criteria

- `make check` in `packages/database` completes successfully and is 100% green.
- `packages/database/tests/e2e/database/conftest.py::wait_for_translations()` no longer raises when the final observed count already satisfies `expected_count`.
- Package-owned background translation can no longer race against e2e teardown in a way that produces dropped/recreated-schema failures such as `relation "words_ru" does not exist`.
- The fix is achieved without skipping tests, inflating timeouts as the primary remedy, adding sleep-based stabilization, or weakening teardown/isolation guarantees.
- Any new or adjusted tests for the repaired behavior are green together with existing package tests.
- No files outside `packages/database` are modified.
- No documentation files other than this task file are modified.
- The work remains a narrow baseline repair and does not start the larger cleanup/refactor.

## Validation Gates

- Run full `make check` from `packages/database`; this is the mandatory end-state gate.
- Treat `lint`, `test-unit`, `test-integration`, and `test-e2e` as equally required because the package `Makefile` composes all of them into `check`.
- Re-run the smallest direct reproducers for both known e2e failure classes before relying on the final full-suite pass.
- Validate that package-owned background translation work is fully settled before e2e teardown destroys or recreates schema.
- Validate that all automated quality gates invoked by `make check` are green unless a blocker/escalation condition is hit and reported.

## Test Expectations

- Keep existing unit, integration, and e2e coverage intact.
- Add or adjust only the package-local tests required to make the repair non-regressing.
- Validation must include linter, dead-code, duplication, and all pytest layers remaining green.
- Any lifecycle regression test should verify deterministic completion or orderly shutdown, not merely eventual success after arbitrary sleeping.
- Follow existing package style and the repo file-size rule; decompose rather than compacting if any file approaches the line-count ceiling.

## Risks

- The lifecycle fix may expose additional hidden assumptions in existing e2e fixtures or service behavior.
- The broad exception handling inside `_translation.translate_and_store()` can make diagnosis harder if task ownership remains implicit.
- Additional `make check` failures may appear only after the current e2e blockers are fixed.
- A tempting but wrong repair is to make teardown less strict instead of fixing task lifecycle ownership.

## Blockers / Escalation Conditions

- If the only viable fix requires touching any module outside `packages/database`, stop immediately and escalate with the exact dependency.
- If debugging proves the failure is caused only by external environment readiness or another module rather than package-owned code/tests, stop and escalate instead of implementing cross-module changes.
- If package docs and the required green-state fix contradict each other, stop and report the contradiction before changing behavior.
- If the only apparent way to get green is to skip tests, weaken isolation, inflate timeouts, or add sleep-based stabilization, stop and escalate because that is explicitly forbidden.

## Done Definition

This task is done only when `packages/database` is back to a fully green `make check` baseline, both the false-negative wait-helper path and the background-translation teardown race are fixed properly inside package scope, and the work remains tightly limited to prerequisite baseline repair before the larger cleanup/refactor.
