---
title: "packages/core + packages/database_cache main protocol and snapshot cleanup"
document_type: "task"
module: "packages/core, packages/database_cache"
status: "done"
---

# Task: Execute the main protocol and snapshot cleanup for `packages/core` and `packages/database_cache`

## Problem Statement

The main cleanup is no longer a `packages/core`-only refactor. The supported target state now spans both `packages/core` and `packages/database_cache`, and the existing task must be revised into one execution-ready cleanup plan that covers both modules together.

`packages/core` still carries legacy protocol/model surfaces that conflict with `packages/core/docs/module-spec.md`, while `packages/database_cache` still consumes removed `core` contracts and still exposes duplicate progress-oriented cache DTO/read APIs that conflict with `packages/database_cache/docs/module-spec.md`. The cleanup must converge both packages on the updated specs without preserving backward compatibility for removed surfaces.

This is the main cleanup task only. The baseline prerequisite repair work is already complete:

- `packages/core` is already green.
- `packages/database_cache` is already green after `packages/database_cache/docs/tasks/baseline-repair-green-check.md`.

That baseline task is not part of this cleanup and must not be reopened or re-scoped into the implementation.

## Why This Exists

- The updated target-state specs for both packages already exist and are now the source of truth.
- `core` and `database_cache` currently disagree with those specs in connected ways, so the cleanup must be planned as one coordinated package pair rather than as isolated edits.
- The user explicitly expanded the cleanup to include `packages/database_cache`, explicitly rejected backward compatibility for removed surfaces, and explicitly limited implementation scope to these two packages only.

## Relevant Context To Read First

### Repo and module docs

- `README.md`
- `packages/core/docs/module-spec.md`
- `packages/database_cache/docs/module-spec.md`
- `packages/core/docs/tasks/baseline-repair-green-check.md`
- `packages/database_cache/docs/tasks/baseline-repair-green-check.md`
- `packages/core/Makefile`
- `packages/database_cache/Makefile`

### `packages/core` source directly involved

- `packages/core/src/nl_processing/core/models.py`
- `packages/core/src/nl_processing/core/protocols.py`
- `packages/core/src/nl_processing/core/progress_models.py`
- `packages/core/src/nl_processing/core/progress_ports.py`
- `packages/core/src/nl_processing/core/ports.py`
- `packages/core/src/nl_processing/core/__init__.py`
- `packages/core/vulture_whitelist.py`

### `packages/database_cache` source directly involved

- `packages/database_cache/src/nl_processing/database_cache/service.py`
- `packages/database_cache/src/nl_processing/database_cache/_service_operations.py`
- `packages/database_cache/src/nl_processing/database_cache/_service_helpers.py`
- `packages/database_cache/src/nl_processing/database_cache/sync.py`
- `packages/database_cache/src/nl_processing/database_cache/ports.py`
- `packages/database_cache/src/nl_processing/database_cache/local_store.py`
- `packages/database_cache/src/nl_processing/database_cache/_local_store_base.py`
- `packages/database_cache/src/nl_processing/database_cache/_local_store_queries.py`
- `packages/database_cache/src/nl_processing/database_cache/detailed_cache.py`
- `packages/database_cache/src/nl_processing/database_cache/detailed_ports.py`
- `packages/database_cache/src/nl_processing/database_cache/__init__.py`
- `packages/database_cache/vulture_whitelist.py`

### Existing tests expected to change or be removed

- `packages/core/tests/unit/core/test_models.py`
- `packages/core/tests/unit/core/test_word_pairs.py`
- `packages/core/tests/unit/core/test_protocols.py`
- `packages/database_cache/tests/unit/database_cache/test_sync.py`
- `packages/database_cache/tests/unit/database_cache/test_personal_vocab.py`
- `packages/database_cache/tests/unit/database_cache/test_service.py`
- `packages/database_cache/tests/unit/database_cache/conftest.py`
- `packages/database_cache/tests/integration/database_cache/test_refresh_rebuild.py`
- `packages/database_cache/tests/integration/database_cache/conftest.py`
- `packages/database_cache/tests/e2e/database_cache/test_personal_vocab_e2e.py`
- Any additional existing tests under either package that still reference removed contract surfaces

## Pre-Implementation Research Results

Treat these findings as established starting context for implementation:

- `packages/core/docs/module-spec.md` and `packages/database_cache/docs/module-spec.md` are the source of truth for the cleanup target state.
- `packages/core` currently still exposes fragmented legacy surfaces in `progress_ports.py`, `ports.py`, and `progress_models.py`, while `packages/core/src/nl_processing/core/protocols.py` already contains the surviving `ScoredPairProvider` contract.
- `packages/core/src/nl_processing/core/models.py` still defines `WordPairSnapshot` without required `added_at`, so current source still lags the target-state spec.
- `packages/database_cache/src/nl_processing/database_cache/service.py`, `packages/database_cache/src/nl_processing/database_cache/_service_operations.py`, and `packages/database_cache/src/nl_processing/database_cache/sync.py` still import `RemoteProgressSyncPort` from `nl_processing.core.progress_ports`, which is incompatible with the target state.
- `packages/database_cache/src/nl_processing/database_cache/service.py` still exposes `list_personal_words()` and `get_progress_summary()` and currently returns `PersonalWord` / `ExerciseProgressSummary` types imported from `nl_processing.database.models`; those APIs are explicitly out of the supported target-state contract.
- `packages/database_cache/src/nl_processing/database_cache/_service_helpers.py` still reconstructs `PersonalWord` objects and computes `ExerciseProgressSummary` DTOs from cache rows, which indicates package-local reliance on duplicate progress-oriented surfaces that the target state removes.
- `packages/database_cache/src/nl_processing/database_cache/sync.py` still depends on `nl_processing.database.models.EnrichedWordPairSnapshot` for `added_at` handling and currently treats `added_at` as conditional; that conflicts with the new canonical `core.WordPairSnapshot` direction where `added_at` is required.
- The local SQLite cache schema in `packages/database_cache/src/nl_processing/database_cache/_local_store_queries.py` already includes `added_at`, so the storage layer is compatible with the target-state snapshot direction.
- `packages/database_cache` already owns `RemoteDeletePort` in `packages/database_cache/src/nl_processing/database_cache/ports.py` and already owns pair-scoped detailed-cache contracts in `detailed_ports.py`; the target-state change is to keep that ownership model and add cache-specific remote sync ownership locally instead of importing it from `core`.
- `packages/database_cache/src/nl_processing/database_cache/detailed_cache.py` already provides `DetailedWordCacheService`, and that public surface stays supported.
- Existing `packages/database_cache` unit, integration, and e2e tests still exercise removed `list_personal_words()` / `get_progress_summary()` behavior and remote fixtures still build `EnrichedWordPairSnapshot` payloads; those tests must be rewritten or removed rather than preserved.
- `packages/database_cache/docs/tasks/baseline-repair-green-check.md` is already marked `done`; implementation must start from today's green state instead of redoing baseline repair.
- Repo-level `README.md` still mentions shared storage contracts in `nl_processing.core.ports`, which is stale relative to the package specs. For this cleanup, the two package module specs override that background doc. Do not let the stale README reintroduce removed surfaces.

## Relevant Skills

- No external API/library web research is required for this cleanup; the work is driven by repo-local contracts.
- If implementation reveals docs drift in either package spec, use the `module-spec-agent` skill guidance to keep `packages/core/docs/module-spec.md` and `packages/database_cache/docs/module-spec.md` target-state, contract-focused, and synchronized with the final implementation.

## Scope

### In Scope

- Complete the contract cleanup across `packages/core` and `packages/database_cache` together.
- In `packages/core`, keep one canonical protocol namespace at `nl_processing.core.protocols` and retain only `ScoredPairProvider`.
- In `packages/core`, make `WordPairSnapshot` the only canonical persisted/snapshot record model and make `added_at` required.
- In `packages/core`, remove legacy `ports.py`, `progress_ports.py`, and `progress_models.py` from supported source and package-local tests.
- In `packages/database_cache`, stop importing cache-specific remote sync/delete contracts from `core` and own those cache-specific contracts locally.
- In `packages/database_cache`, align the supported scored-read contract to canonical `core.WordPairSnapshot`.
- In `packages/database_cache`, remove `list_personal_words()` and `get_progress_summary()` from the supported contract and remove package-local duplicate progress DTO reliance when the same information is derivable from canonical snapshots.
- Keep `DetailedWordCacheService` as the supported detailed-cache surface.
- Remove unauthorized legacy surfaces from source, tests, and package-local tooling when they are no longer part of the supported contract.
- Keep docs and code synchronized for both affected package specs if implementation reveals any remaining drift.

### Out of Scope

- Reopening or extending the already-completed `packages/database_cache` baseline repair task.
- Any implementation work in `packages/database`, `packages/database_core`, or any other package.
- Preserving import compatibility for removed surfaces.
- Introducing compatibility shims, aliases, wrappers, deprecated re-exports, or fallback DTOs.
- Root-level doc cleanup outside the two affected package specs.
- New feature work unrelated to the protocol/model contract cleanup.

## Dependencies

### Contract and documentation dependencies

- `packages/core/docs/module-spec.md` is the authoritative target-state contract for `packages/core`.
- `packages/database_cache/docs/module-spec.md` is the authoritative target-state contract for `packages/database_cache`.
- `packages/database_cache/docs/tasks/baseline-repair-green-check.md` is completion evidence for the prerequisite baseline and must be treated as already satisfied, not as active work.

### Code and tooling dependencies

- `packages/core/Makefile` defines `packages/core` completion through fully green `make check`.
- `packages/database_cache/Makefile` defines `packages/database_cache` completion through fully green `make check`.
- `packages/database_cache` tests run with package-local `PYTHONPATH` composition including `../core/src` and `../database/src`, so contract cleanup in one package will surface in the other package's checks.
- Pydantic v2 remains the model layer for canonical `core` value models.
- Existing quality gates include Ruff, pylint, vulture, jscpd, and pytest via package-local `make check`.

## Explicit Target-State Decisions

The implementer must treat all of the following as already decided. Do not reopen them during implementation:

1. Only two modules are in scope: `packages/core` and `packages/database_cache`.
2. `packages/core/docs/module-spec.md` and `packages/database_cache/docs/module-spec.md` are the source of truth.
3. `nl_processing.core.protocols` is the only supported public protocol namespace in `core`.
4. `ScoredPairProvider` is the only supported public protocol contract that remains in `core`.
5. `packages/core/src/nl_processing/core/ports.py` must be removed.
6. `packages/core/src/nl_processing/core/progress_ports.py` must be removed.
7. `packages/core/src/nl_processing/core/progress_models.py` must be removed.
8. `WordPairSnapshot` in `packages/core/src/nl_processing/core/models.py` is the only canonical persisted/snapshot record model supported by `core`.
9. `WordPairSnapshot` must include pair data, scores, stable source/target identifiers, and required `added_at`.
10. `EnrichedWordPairSnapshot`, `PersonalWord`, and `ExerciseProgressSummary` are removed from the supported `core` contract and must not survive in `core` source/tests.
11. `database_cache` must stop importing cache-specific remote sync/delete contracts from `core`.
12. `database_cache` must own its cache-specific remote sync/delete contracts inside `packages/database_cache/src/nl_processing/database_cache/`.
13. The supported scored read contract in `database_cache` is canonical `core.WordPairSnapshot`, not a cache-specific duplicate record model.
14. `DatabaseCacheService.list_personal_words()` is removed from the supported target-state contract and should be removed from source/tests unless implementation discovers it is still needed inside `packages/database_cache` itself for a supported surface, in which case stop and escalate instead of preserving it ad hoc.
15. `DatabaseCacheService.get_progress_summary()` is removed from the supported target-state contract and should be removed from source/tests unless implementation discovers a spec contradiction, in which case stop and escalate.
16. `database_cache` must not keep package-local duplicate progress DTO flows where the same information is derivable from canonical snapshot rows.
17. `DetailedWordCacheService` remains a supported public surface and must stay intact.
18. No backward compatibility layer is required for removed files, APIs, imports, models, fixtures, or test helpers.
19. If implementation reveals that either package spec still drifts from the final supported code, the implementer must update that package's `docs/module-spec.md` in the same cleanup so docs and code remain synchronized.
20. If implementation would require touching `packages/database` or any module outside `packages/core` and `packages/database_cache`, stop immediately and escalate instead of widening scope.

## Pre-Implementation Research To Confirm Before Editing

Before making changes, re-confirm these concrete starting points in live source so implementation proceeds from facts, not stale assumptions:

1. `packages/core/src/nl_processing/core/models.py` still lacks `added_at` on `WordPairSnapshot`.
2. `packages/core/src/nl_processing/core/progress_ports.py`, `packages/core/src/nl_processing/core/progress_models.py`, and `packages/core/src/nl_processing/core/ports.py` still exist.
3. `packages/database_cache/src/nl_processing/database_cache/service.py`, `_service_operations.py`, and `sync.py` still import `RemoteProgressSyncPort` from `nl_processing.core.progress_ports`.
4. `packages/database_cache/src/nl_processing/database_cache/service.py` still defines `list_personal_words()` and `get_progress_summary()`.
5. `packages/database_cache` tests still contain assertions built around `PersonalWord`, `ExerciseProgressSummary`, or legacy enriched snapshot fixtures.
6. Both packages still start from green `make check` before the cleanup begins.

## Explicit File Scope Expectations For Implementation

Expected primary file scope in `packages/core`:

- `packages/core/src/nl_processing/core/models.py`
- `packages/core/src/nl_processing/core/protocols.py`
- `packages/core/src/nl_processing/core/progress_models.py`
- `packages/core/src/nl_processing/core/progress_ports.py`
- `packages/core/src/nl_processing/core/ports.py`
- `packages/core/src/nl_processing/core/__init__.py`
- `packages/core/tests/unit/core/test_models.py`
- `packages/core/tests/unit/core/test_word_pairs.py`
- `packages/core/tests/unit/core/test_protocols.py`
- `packages/core/vulture_whitelist.py`
- `packages/core/docs/module-spec.md` only if implementation confirms remaining docs drift

Expected primary file scope in `packages/database_cache`:

- `packages/database_cache/src/nl_processing/database_cache/service.py`
- `packages/database_cache/src/nl_processing/database_cache/_service_operations.py`
- `packages/database_cache/src/nl_processing/database_cache/_service_helpers.py`
- `packages/database_cache/src/nl_processing/database_cache/sync.py`
- `packages/database_cache/src/nl_processing/database_cache/ports.py`
- `packages/database_cache/src/nl_processing/database_cache/local_store.py`
- `packages/database_cache/src/nl_processing/database_cache/_local_store_base.py`
- `packages/database_cache/src/nl_processing/database_cache/_local_store_queries.py`
- `packages/database_cache/src/nl_processing/database_cache/__init__.py`
- `packages/database_cache/tests/unit/database_cache/conftest.py`
- `packages/database_cache/tests/unit/database_cache/test_sync.py`
- `packages/database_cache/tests/unit/database_cache/test_personal_vocab.py`
- `packages/database_cache/tests/unit/database_cache/test_service.py`
- `packages/database_cache/tests/integration/database_cache/conftest.py`
- `packages/database_cache/tests/integration/database_cache/test_refresh_rebuild.py`
- `packages/database_cache/tests/e2e/database_cache/test_personal_vocab_e2e.py`
- `packages/database_cache/vulture_whitelist.py`
- `packages/database_cache/docs/module-spec.md` only if implementation confirms remaining docs drift

Conditionally allowed only if directly required by package-local references or by `make check` failures inside the two scoped modules:

- Other existing files under `packages/core/src/nl_processing/core/`
- Other existing files under `packages/core/tests/`
- Other existing files under `packages/database_cache/src/nl_processing/database_cache/`
- Other existing files under `packages/database_cache/tests/`
- Other existing docs inside `packages/core/docs/` or `packages/database_cache/docs/` only when they directly describe the removed or changed supported contract

Not allowed:

- Any file outside `packages/core` or `packages/database_cache`
- Any edit to `packages/database/docs/module-spec.md`
- Any edit to source/tests/docs in `packages/database` or other modules as part of this cleanup
- New compatibility modules or placeholder legacy modules to preserve removed imports

## Implementation Plan

1. Re-read both package specs and treat them as the authoritative target state.
2. Re-confirm that both packages start green by running `make check` in `packages/core` and `packages/database_cache` before making cleanup edits.
3. In `packages/core`, update `WordPairSnapshot` so it becomes the one canonical persisted/snapshot record model with required `added_at`.
4. In `packages/core`, keep `protocols.py` as the only supported protocol module and ensure it contains only `ScoredPairProvider` with the final supported scored-pair return contract.
5. In `packages/core`, delete `progress_models.py`, `progress_ports.py`, and `ports.py` instead of preserving aliases or shims.
6. In `packages/core`, update `__init__.py`, tests, and `vulture_whitelist.py` so no surviving source or tests reference removed legacy protocol/model surfaces.
7. In `packages/database_cache`, introduce or finalize a package-local cache-specific remote sync contract alongside the already package-owned delete contract, then switch `service.py`, `_service_operations.py`, `sync.py`, and related tests/fixtures to that local contract.
8. In `packages/database_cache`, update refresh/snapshot handling to consume canonical `core.WordPairSnapshot` records directly rather than depending on `database.models.EnrichedWordPairSnapshot` or conditional `added_at` handling.
9. In `packages/database_cache`, update `get_word_pairs_with_scores()` so it reconstructs canonical `WordPairSnapshot` values including required `added_at` from persisted cache rows.
10. In `packages/database_cache`, remove `list_personal_words()` and `get_progress_summary()` from supported source and delete or rewrite any package-local helpers, fixtures, and tests that exist only to support those removed APIs or duplicate DTOs.
11. Keep `DetailedWordCacheService` and its detailed-cache tests intact except where indirect contract fallout requires import or fixture cleanup.
12. Remove unauthorized legacy surfaces from source/tests/tooling in both packages as part of the cleanup itself; do not leave dead code, dead tests, dead whitelist entries, or compatibility placeholders behind.
13. Compare final code against both package specs. If implementation reveals any remaining docs/code drift in `packages/core/docs/module-spec.md` or `packages/database_cache/docs/module-spec.md`, update the affected package spec in the same task so docs remain authoritative.
14. Run `make check` in `packages/core` and fix every package-local regression without reintroducing removed legacy surfaces.
15. Run `make check` in `packages/database_cache` and fix every package-local regression without restoring removed APIs or core-owned cache contracts.
16. If either package cannot be completed without touching `packages/database` or another out-of-scope module, stop immediately and escalate with the exact dependency and failing path.

## Required Implementation Notes

- This task is the main cleanup for both scoped modules; it is not a baseline repair task.
- Remove unauthorized legacy surfaces from source and tests once they are no longer part of the supported contract.
- Prefer deletion over deprecation, aliasing, or wrapper preservation.
- Keep the architecture boundary explicit: `core` owns only shared canonical models and the one surviving generic protocol; `database_cache` owns cache-specific remote contracts.
- Do not keep duplicate progress DTOs in `database_cache` when the same data is derivable from canonical snapshot rows.
- Do not silently widen module scope. If a required change points at `packages/database` or another package, stop and escalate.
- Follow the repo file-size rule. If cleanup causes a touched file to approach the line limit, decompose it instead of compacting logic.

## Acceptance Criteria

- `packages/core/src/nl_processing/core/protocols.py` is the only supported public protocol surface in `core`.
- `ScoredPairProvider` is the only supported public protocol contract left in `packages/core`.
- `packages/core/src/nl_processing/core/ports.py` is removed.
- `packages/core/src/nl_processing/core/progress_ports.py` is removed.
- `packages/core/src/nl_processing/core/progress_models.py` is removed.
- `packages/core/src/nl_processing/core/models.py` exposes `WordPairSnapshot` as the sole persisted/snapshot record model and includes required `added_at` alongside pair data, score data, and stable IDs.
- `packages/database_cache` no longer imports cache-specific remote sync/delete contracts from `nl_processing.core`.
- `packages/database_cache` owns its supported cache-specific remote sync/delete contracts locally.
- `packages/database_cache.get_word_pairs_with_scores()` returns canonical `core.WordPairSnapshot` values, including required `added_at` reconstructed from persisted cache data.
- `packages/database_cache.service.DatabaseCacheService` no longer exposes supported `list_personal_words()` or `get_progress_summary()` APIs.
- Package-local helpers, fixtures, tests, and whitelist/config references that only existed for removed surfaces are deleted or rewritten rather than preserved.
- `DetailedWordCacheService` remains available as the supported detailed cache surface.
- `packages/core/docs/module-spec.md` and `packages/database_cache/docs/module-spec.md` are updated if, and only if, implementation reveals remaining drift; final docs and code match.
- No compatibility shim, alias, or deprecated wrapper is added for removed surfaces.
- No files outside `packages/core` and `packages/database_cache` are modified.
- `make check` in `packages/core` is 100% green at completion.
- `make check` in `packages/database_cache` is 100% green at completion.

## Validation Gates

- Run full `make check` in `packages/core`; this is mandatory and must finish fully green.
- Run full `make check` in `packages/database_cache`; this is mandatory and must finish fully green.
- Confirm source and tests in both packages no longer import `nl_processing.core.ports`, `nl_processing.core.progress_ports`, or `nl_processing.core.progress_models`.
- Confirm removed `list_personal_words()` / `get_progress_summary()` surfaces are not still being validated by package-local tests as supported API.
- Confirm `WordPairSnapshot` validation now requires `added_at` and that both packages use the same canonical snapshot contract.
- Confirm `packages/database_cache` fixtures/tests no longer depend on `EnrichedWordPairSnapshot`, `PersonalWord`, or `ExerciseProgressSummary` as supported cleanup-end-state contract surfaces when canonical snapshots are sufficient.
- Confirm lint/dead-code/duplication tooling in both packages no longer reports dead references to removed legacy names.
- Confirm final docs/code review against both package specs shows no remaining supported-contract mismatch.

## Test Expectations

- Update existing tests to validate only the supported target-state contract.
- Remove or rewrite tests that exist solely to preserve removed legacy surfaces.
- Add or adjust only the tests needed to prove the canonical snapshot and local-contract ownership behavior after the cleanup.
- Ensure all automated quality gates invoked by each package's `make check` remain green unless an explicit blocker is hit and escalated.
- Follow existing repo code style and decomposition rules; do not compact code to satisfy file-length limits.

## Risks

- Removing `core` legacy surfaces may expose hidden `database_cache` or test-only dependencies that were previously masked by compatibility imports.
- `database_cache` currently mixes canonical snapshot reads with duplicate progress DTO helpers; cleanup may cascade across more tests and fixtures than the current file names initially suggest.
- Repo-level docs outside the two package specs are already partially stale, which can tempt implementers to preserve removed surfaces incorrectly.
- If any real remaining consumer of removed surfaces lives outside the two scoped modules, the cleanup will correctly hit a boundary stop rather than silently widening scope.

## Blockers / Escalation Conditions

- If implementing the target-state cleanup requires touching `packages/database` or any module outside `packages/core` and `packages/database_cache`, stop immediately and escalate.
- If `make check` in either scoped package cannot be restored to green without restoring removed surfaces or adding compatibility shims, stop and escalate.
- If implementation reveals a contradiction between the two package specs that cannot be resolved inside `packages/core/docs/module-spec.md` and `packages/database_cache/docs/module-spec.md`, stop and report the contradiction before changing behavior further.
- If a removed surface appears to still be required for a supported contract but that need is not already documented in the package specs, stop and escalate instead of reintroducing it ad hoc.
- If final code would force docs drift in either affected package spec and the drift cannot be resolved inside those specs, stop and escalate rather than leaving code/docs out of sync.

## Done Definition

This task is done only when `packages/core` and `packages/database_cache` both match their updated module specs, `core` exposes only the canonical protocol and snapshot surfaces, `database_cache` owns its cache-specific contracts and exposes only canonical snapshot-based supported read behavior plus `DetailedWordCacheService`, unauthorized legacy surfaces are removed from source/tests/tooling, both affected package specs are synchronized if needed, and `make check` is fully green in both packages.
