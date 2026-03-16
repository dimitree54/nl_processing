---
title: "packages/database_cache baseline green-check repair"
document_type: "task"
module: "packages/database_cache"
status: "done"
---

# Task: Restore `packages/database_cache` baseline green state

## Problem Statement

`packages/database_cache` is not currently at a clean package baseline. This prerequisite task exists to restore a fully green `make check` in `packages/database_cache` before the broader cross-module cleanup/refactor continues.

`packages/database_cache/Makefile` defines `make check` as `lint` plus `test`, and `test` expands to unit, integration, and e2e suites. The latest known blocker is in e2e:

- `tests/e2e/database_cache/test_full_loop.py::test_full_lifecycle_init_read_write_flush`
- failure originates in `tests/e2e/database_cache/conftest.py::wait_for_translations`
- assertion: `Translations did not complete within 15.0s (expected=3, actual=0)`

There was also a previous failure with the same timeout shape in `tests/e2e/database_cache/test_personal_vocab_e2e.py::test_delete_word_removes_from_cache_and_remote`, which strongly suggests the breakage is in the e2e seed/setup translation path rather than in one isolated assertion.

Unit and integration tests reportedly passed in the latest run, but unit tests emitted a `PytestUnhandledThreadExceptionWarning` from `aiosqlite` after the suite finished. That warning is not allowed to be ignored if it reflects a reproducible lifecycle defect in package code or tests.

This task is intentionally narrow. Do not begin the larger protocol/model/architecture cleanup here.

## Why This Exists

- The larger cleanup/refactor must start from a known-green `packages/database_cache` baseline.
- The current failing e2e setup obscures whether later failures belong to the planned refactor or to pre-existing package instability.
- The package owns a real local-cache lifecycle with async background work and live e2e coverage; baseline health matters before any architectural change.

## Relevant Context To Read First

### Repo and module docs

- `README.md`
- `docs/module-spec.md`
- `packages/database_cache/Makefile`
- `packages/database_cache/docs/module-spec.md`
- `packages/database/docs/module-spec.md`

### Source and tests directly relevant to the current failure surface

- `packages/database_cache/src/nl_processing/database_cache/service.py`
- `packages/database_cache/src/nl_processing/database_cache/sync.py`
- `packages/database_cache/src/nl_processing/database_cache/local_store.py`
- `packages/database_cache/src/nl_processing/database_cache/_local_store_base.py`
- `packages/database_cache/src/nl_processing/database_cache/_service_helpers.py`
- `packages/database_cache/tests/e2e/database_cache/conftest.py`
- `packages/database_cache/tests/e2e/database_cache/test_full_loop.py`
- `packages/database_cache/tests/e2e/database_cache/test_personal_vocab_e2e.py`
- `packages/database_cache/tests/unit/database_cache/conftest.py`
- `packages/database_cache/tests/unit/database_cache/test_service.py`
- `packages/database_cache/tests/integration/database_cache/test_refresh_rebuild.py`

### Read-only upstream context for the e2e seed path

- Reading these files for diagnosis is allowed and expected.
- Modifying these files is not allowed in this task.

- `packages/database/src/nl_processing/database/service.py`
- `packages/database/src/nl_processing/database/testing.py`

## Pre-Implementation Research Results

These findings are already established from repo inspection and the reported failures. Treat them as starting context for the repair:

- `packages/database_cache/Makefile` requires `lint`, `test-unit`, `test-integration`, and `test-e2e` through `make check`; completion means the full package gate is green, not only the currently failing test.
- `tests/e2e/database_cache/conftest.py::seed_words()` creates a real `DatabaseService` with a real `WordTranslator`, awaits `service.add_words(WORDS)`, and only then calls `wait_for_translations(len(WORDS), backend=backend)`.
- `wait_for_translations()` polls `count_translation_links("nl_ru")` once per second for up to 15 seconds and fails only if the remote `translations_nl_ru` row count stays below the expected count. The known failure is `expected=3, actual=0`, which means no translation links were observed at all during the polling window.
- `seed_words()` does not instantiate or call `DatabaseCacheService` until after translations are expected to exist, so the current known blocker is before cache init/read/write behavior. The first diagnosis target is the e2e seed/setup path, not the cache assertions later in the tests.
- In read-only upstream context, `packages/database/src/nl_processing/database/service.py::add_words()` awaits canonical word persistence and `add_user_word(...)`, but it does not await translation completion.
- Instead, when there are new source-language words and a translator is configured, `add_words()` schedules translation with `asyncio.create_task(self._delayed_translation(new_source_word_pairs))` and returns immediately.
- `_delayed_translation()` then creates a fresh Neon backend for real backends and awaits `_translation.translate_and_store(...)` on that background task. This means the database_cache e2e seed path is explicitly dependent on background translation reaching completion after `add_words()` has already returned.
- Because the failing shape is `actual=0` rather than a partial count, the likely boundary is one of these: the background translation task never starts, starts but fails before inserting any translation links, or the package e2e setup waits on the wrong completion signal for the way upstream translation actually completes.
- That boundary is important: package-local repair may still be possible if the issue is in database_cache-owned test orchestration or async lifecycle assumptions, but if diagnosis proves the translation task itself is broken upstream then implementation must stop and escalate.
- The same timeout shape hit at least two e2e tests, which makes a one-off assertion bug unlikely.
- `DatabaseCacheService.record_exercise_result()` also schedules background work with `asyncio.create_task(background_flush(...))` and the service has no explicit close/shutdown API today.
- `LocalStoreBase` owns the underlying `aiosqlite` connection and exposes `close()`, while tests commonly close stores directly; this is a credible investigation target for the observed post-suite `aiosqlite` thread warning.
- Package-local async lifecycle risk is already visible in tests: some fixtures use `await asyncio.sleep(0)` during teardown, and at least one unit test monkeypatches `asyncio.create_task` and manually closes the created coroutine. That is useful context when investigating orphaned tasks and `aiosqlite` teardown warnings.
- The current package doc `packages/database_cache/docs/module-spec.md` describes cache refresh/flush semantics and local durability, but this baseline repair must not edit that doc. Only this task file may be added or changed.

## Async Lifecycle Guidance Already Established

Use these as implementation research constraints, not as optional ideas:

- If package-owned code creates background tasks with `asyncio.create_task(...)`, a proper repair should track, await, cancel, or otherwise shut them down explicitly before fixture/service teardown. Do not leave package-owned tasks orphaned.
- Prefer explicit service/store lifecycle methods such as `close()` or `shutdown()` semantics over timing sleeps in teardown.
- If a store owns an `aiosqlite` connection, orderly closure should happen after pending package-owned operations that touch that connection are complete.
- Fix `aiosqlite` lifecycle issues by awaiting/closing work in order. Do not silence the warning, filter it, or rely on incidental loop timing.
- If a package-local test currently relies on `await asyncio.sleep(0)` just to let background work settle, treat that as a likely smell to reassess rather than the preferred final design.

## Relevant Skills

- No specialized implementation skill is required for this repair.
- Do not expand this work into `feature-request`, `bug-report`, or broader spec-rewrite workflows; this is a prerequisite baseline repair only.
- `set-up-env-vars` is not part of implementation. If execution proves the failure is caused only by missing/bad Doppler configuration instead of package code or tests, stop and escalate rather than changing environment setup in this task.

## Scope

### In Scope

- Reproduce the current `packages/database_cache` failure state and restore a fully green `make check`.
- Properly fix the e2e translation-timeout failure affecting the package's live cache workflow.
- Investigate the full e2e seed/setup path used by `tests/e2e/database_cache/conftest.py`, including whether the regression is in package-owned test orchestration, package-owned async lifecycle handling, or package-owned assumptions about upstream translation completion.
- Investigate the non-fatal `PytestUnhandledThreadExceptionWarning` from `aiosqlite`; if it is reproducible and caused by `packages/database_cache` code or tests, fix it in this task.
- Make the minimum coherent source/test changes inside `packages/database_cache` required to restore package health without weakening quality gates.

### Out of Scope

- The larger cross-module cleanup/refactor.
- Protocol/model redesign.
- Changes outside `packages/database_cache`.
- Documentation updates other than this task file.
- Any edit to `packages/database_cache/docs/module-spec.md`.
- Disabling, skipping, xfail-marking, quarantining, or loosening tests/checks to manufacture a green result.
- Doppler/env-var changes, unless the user explicitly creates a separate task for environment management.

## Dependencies

### Code and contract dependencies

- `packages/database_cache/Makefile` is the package completion contract.
- `packages/database_cache/docs/module-spec.md` is background context for expected cache behavior, but must remain unchanged in this task.
- `packages/database/docs/module-spec.md` documents that `database.add_words()` schedules background translation and that read APIs return only completed translation pairs.

### Runtime and tooling dependencies

- `uv` for package environment sync and command execution.
- `doppler run` for integration/e2e environment injection.
- Ruff, pylint, vulture, jscpd, and pytest as invoked by `make check`.
- Live Neon-backed e2e execution through the package's existing test setup.

## Explicit File Scope Expectations For Implementation

Implementation must stay inside `packages/database_cache`.

Expected primary file scope:

- `packages/database_cache/src/nl_processing/database_cache/service.py`
- `packages/database_cache/src/nl_processing/database_cache/sync.py`
- `packages/database_cache/src/nl_processing/database_cache/local_store.py`
- `packages/database_cache/src/nl_processing/database_cache/_local_store_base.py`
- `packages/database_cache/src/nl_processing/database_cache/_service_helpers.py`
- `packages/database_cache/tests/e2e/database_cache/conftest.py`
- `packages/database_cache/tests/e2e/database_cache/test_full_loop.py`
- `packages/database_cache/tests/e2e/database_cache/test_personal_vocab_e2e.py`
- `packages/database_cache/tests/unit/database_cache/conftest.py`
- `packages/database_cache/tests/unit/database_cache/test_service.py`
- `packages/database_cache/tests/integration/database_cache/test_refresh_rebuild.py`

Conditionally allowed only if directly required by reproduced failures uncovered during repair:

- Other existing files under `packages/database_cache/src/nl_processing/database_cache/`
- Other existing files under `packages/database_cache/tests/`
- Existing package-local config files under `packages/database_cache/` only if a reproduced `make check` failure proves a config issue inside this package

Not allowed:

- Any file outside `packages/database_cache`
- Any docs other than this task file
- `packages/database_cache/docs/module-spec.md`
- Source/test changes whose only purpose is to skip or soften failing checks

## Implementation Plan

1. Reproduce the package baseline locally by running `make check` in `packages/database_cache`, and capture exactly which gate fails first now.
2. Re-run the failing e2e tests directly to confirm whether the current break remains the translation timeout reported in `wait_for_translations()` and whether both timeout-shaped failures still reproduce.
3. Trace the package-owned e2e setup path end to end:
   - `tests/e2e/database_cache/conftest.py::seed_words()`
   - `DatabaseService.add_words()` background translation behavior as consumed by these tests
   - the moment `DatabaseCacheService.init()` first becomes relevant
4. Determine whether the package can and should make the e2e setup deterministic from within `packages/database_cache` without changing upstream modules. Favor a proper package-local repair such as fixing package-owned test orchestration, package-owned waiting assumptions, or package-owned async/lifecycle handling. Do not mask the failure with longer arbitrary waits unless root-cause analysis proves the existing timeout is simply below the package's documented, acceptable completion window.
5. If the actual root cause is in package runtime code, fix it in `packages/database_cache` and add or adjust package-local coverage so the repaired behavior is protected.
6. Investigate the `aiosqlite` warning separately:
   - reproduce it with the narrowest package-local command possible
   - determine whether it is caused by untracked background tasks, missing store/service shutdown, or test fixture teardown order
   - if it is reproducible and caused by package code/tests, fix it in this task
7. Re-run targeted unit, integration, and e2e tests after each fix until all previously failing paths are stable.
8. Finish by running full `make check` in `packages/database_cache` and fixing any additional package-local regressions uncovered on the way.

## Required Decision Rules During Implementation

- Treat this as a prerequisite baseline repair before the larger cleanup/refactor, not as the cleanup itself.
- Fix the e2e translation-timeout failure properly. Do not skip tests, mark them flaky, add xfails, or weaken package checks.
- Prefer the smallest proper repair that restores the documented package contract and package stability.
- Preserve fail-fast behavior. Do not add silent fallbacks, hidden retries, or exception swallowing to make tests pass.
- Reading upstream files under `packages/database/...` for diagnosis is allowed; modifying them is not.
- If a proposed fix would require changing `packages/database`, `packages/core`, `packages/translate_word`, or any other module, stop and escalate instead of implementing across module boundaries.
- If the `aiosqlite` warning is non-reproducible or clearly external to `packages/database_cache`, document that evidence in the implementation notes/PR summary; otherwise fix it here.

## Proper Fix vs Unacceptable Workaround

### Counts As A Proper Fix

- Making package-owned async lifecycle deterministic, for example by adding explicit shutdown/close handling for package-owned background work.
- Updating package-local fixtures/tests so they wait on the correct package-owned completion condition instead of incidental loop timing.
- Adjusting package-local cache/service code so pending flush/refresh work does not outlive owned SQLite resources.
- Adding or tightening package-local regression coverage that proves the repaired async behavior and clean teardown.

### Does Not Count As A Proper Fix

- Increasing `wait_for_translations()` timeout without root-cause evidence that 15 seconds is simply too short for a healthy, deterministic path.
- Adding `sleep(...)` in fixtures or tests as the main stabilization strategy.
- Filtering, suppressing, or ignoring `PytestUnhandledThreadExceptionWarning` from `aiosqlite`.
- Skipping, xfail-marking, or quarantining failing e2e or unit tests.
- Catching and discarding async exceptions from background work just so teardown looks clean.

## Escalation Decision Tree

Use this order and stop as soon as one stop condition is proven:

1. Confirm whether the timeout occurs before any `DatabaseCacheService` behavior is exercised. Current research says yes.
2. Check whether package-local e2e orchestration is waiting on the right signal for the upstream async translation model.
3. Check whether package-owned async teardown or background work is leaving SQLite work unfinished and causing the `aiosqlite` warning.
4. If a package-local fix makes the seed/setup deterministic and keeps package teardown clean, implement it and continue to green `make check`.
5. If diagnosis proves the upstream `database.add_words()` background translation task never starts, fails before writing any links, or otherwise requires changes in `packages/database` or another module, stop and escalate with the exact evidence.
6. If diagnosis proves the only issue is environment readiness or external service availability rather than package-owned code/tests, stop and escalate with the exact failing dependency.
7. If the only apparent package-local option is timeout inflation, sleeps, warning suppression, or test weakening, stop and escalate because that is not an acceptable repair.

## Acceptance Criteria

- `make check` in `packages/database_cache` completes successfully and is 100% green.
- The e2e failure in `tests/e2e/database_cache/test_full_loop.py::test_full_lifecycle_init_read_write_flush` no longer times out waiting for translations.
- The same underlying timeout shape no longer affects `tests/e2e/database_cache/test_personal_vocab_e2e.py::test_delete_word_removes_from_cache_and_remote`.
- The repair is achieved without disabling/skipping tests, without increasing laxity of package checks, and without introducing fallback behavior that hides real failures.
- If the `PytestUnhandledThreadExceptionWarning` from `aiosqlite` is reproducible and caused by package code/tests, it is fixed as part of this task.
- No files outside `packages/database_cache` are modified.
- No documentation files other than this task file are modified.
- No architectural cleanup/refactor work beyond baseline repair is pulled into the change.

## Validation Gates

- Run full `make check` from `packages/database_cache`; this is the mandatory end-state gate.
- Treat `lint`, `test-unit`, `test-integration`, and `test-e2e` as equally required because the package `Makefile` composes all of them into `check`.
- Re-run the two translation-timeout-shaped e2e tests directly during diagnosis before relying on the final full-suite pass.
- Re-run the smallest reproducer for the `aiosqlite` warning to confirm whether it is fixed or truly not attributable to package code/tests.
- Produce package-local evidence for async lifecycle health: no package-owned background task should still be touching SQLite after owned store/service teardown.
- All automated quality gates invoked by `make check` must be green unless a blocker/escalation condition is hit and reported.

## Test Expectations

- Keep existing package-local unit, integration, and e2e coverage intact.
- Add or adjust only the package-local tests needed to make the repaired behavior stable and non-regressing.
- Ensure linter, dead-code, duplication, and all pytest layers remain green after the fix.
- For the async lifecycle issue, produce package-local verification that teardown is orderly: either a regression test or a tightly scoped reproducer shows that package-owned resources close cleanly without the prior `aiosqlite` warning.
- If the `aiosqlite` warning was reproducible before the fix, final validation should include rerunning the same package-local reproducer and confirming the warning no longer appears.
- If the warning cannot be reproduced after careful package-local isolation, record the exact commands used and why the evidence supports leaving package code unchanged.
- Follow existing package style and file-size rules; decompose rather than compacting if any file approaches the line-count ceiling.

## Risks

- The timeout may be caused by a real regression in upstream translation behavior rather than by package-owned code; in that case this task will hit a hard module-boundary stop.
- The e2e failure may stem from nondeterministic background-task timing, which can tempt a superficial timeout increase instead of a real lifecycle fix.
- Repairing async teardown may expose hidden ordering assumptions in existing tests or fixtures.
- Additional `make check` failures may appear only after the current e2e blocker is fixed.

## Blockers / Escalation Conditions

- If the only viable fix requires touching any module outside `packages/database_cache`, stop immediately and escalate with the exact external dependency.
- If debugging proves the translation timeout is caused by `packages/database`, `packages/translate_word`, shared infrastructure, or environment readiness rather than package-owned code/tests, stop and escalate instead of implementing cross-module changes.
- If the package docs and the required green-state fix contradict each other, stop and report the contradiction before changing behavior.
- If the only apparent way to get green is to skip, xfail, quarantine, or weaken tests/checks, stop and escalate; that is explicitly forbidden.
- If the `aiosqlite` warning indicates a deeper lifecycle issue that cannot be fixed without external-module changes, report the evidence and stop.

## Done Definition

This task is done only when `packages/database_cache` is back to a fully green `make check` baseline, the e2e translation-timeout failure is fixed properly inside package scope, any reproducible package-owned `aiosqlite` lifecycle warning is resolved, and the work remains tightly limited to prerequisite baseline repair.
