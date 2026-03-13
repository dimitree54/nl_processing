---
Task ID: T1
Title: Add shared tiered DTOs and provider protocol to `core`
Sprint: `2026-03-14_tiered-mixed-exercise`
Module: core
Depends on: --
Parallelizable: no (all other tasks depend on this)
---

## Goal / value

After this task, `core` exposes the shared tiered data models (`TieredCandidate`, `TieredExerciseSelection`, `TieredProgressSummary`, `TieredSnapshotEntry`) and the `TieredCandidateProvider` protocol that `database`, `database_cache`, and `sampling` will depend on. This prevents circular cross-package imports and establishes the typed contract before any implementation starts.

## Context (contract mapping)

- Database spec: `packages/database/docs/module-spec.md` Section 5 (TIF-DB-1, TIF-DB-3)
- Cache spec: `packages/database_cache/docs/module-spec.md` Section 5 (TIF-DC-1, TIF-DC-4)
- Sampling spec: `packages/sampling/docs/module-spec.md` Section 5 (TIF-1, TIF-2, TOQ-1)
- Core models: `packages/core/src/nl_processing/core/models.py`
- Core ports: `packages/core/src/nl_processing/core/ports.py`

## Preconditions

- `make -C packages/core check` passes before starting.

## Non-goals

- Implementing any tiered business logic (stores, caches, samplers).
- Modifying existing `ScoredWordPair`, `WordPairSnapshot`, `ScoredPairProvider`, or `RemoteProgressSyncPort`.
- Adding repeat-state transition logic (that belongs in `database` and `database_cache`).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**

- `packages/core/src/nl_processing/core/` -- add new tiered model and port files
- `packages/core/tests/` -- add tests for new models and ports

**FORBIDDEN -- this task must NEVER touch:**

- `packages/database/`, `packages/database_cache/`, `packages/sampling/`
- Existing `models.py` or `ports.py` in `core` (unless adding exports to `__init__.py`)
- `docs/`, `Makefile`, `pyproject.toml`, `ruff.toml`

**Test scope:**

- Tests go in: `packages/core/tests/unit/core/`
- Test command: `make -C packages/core check`
- NEVER run the full test suite or tests from other modules

## Touched surface (expected files / modules)

- NEW: `packages/core/src/nl_processing/core/tiered_models.py` -- tiered DTOs
- NEW: `packages/core/src/nl_processing/core/tiered_ports.py` -- tiered provider protocol and remote sync protocol
- NEW: `packages/core/tests/unit/core/test_tiered_models.py` -- model unit tests
- NEW: `packages/core/tests/unit/core/test_tiered_ports.py` -- protocol structural conformance tests

## Dependencies and sequencing notes

- This is the foundation task. All other tasks (T2, T3, T4) depend on the DTOs and protocol defined here.
- No external dependencies or third-party research needed; uses only `pydantic.BaseModel` and `typing.Protocol` which are already in use in `core`.

## Third-party / library research (mandatory for any external dependency)

No new third-party dependencies. This task uses only:

- **pydantic** (already used in `core/models.py` for `BaseModel`)
- **typing.Protocol** (already used in `core/ports.py` for `ScoredPairProvider`)

## Implementation steps (developer-facing)

1. **Create `packages/core/src/nl_processing/core/tiered_models.py`**:
   - `TieredCandidate(BaseModel)` with fields: `pair: WordPair`, `source_word_id: int`, `scores: dict[str, int]`, `in_repeat_mode: bool`. The `scores` dict is keyed by exercise type with integer score values. Missing exercises are not expected here -- the provider must supply all participating scores (defaulting to 0).
   - `TieredExerciseSelection(BaseModel)` with fields: `pair: WordPair`, `source_word_id: int`, `exercise_type: str`, `in_repeat_mode: bool`.
   - `TieredProgressSummary(BaseModel)` with fields: `total_words: int`, `fully_completed_words: int`, `completion_ratio: float`. A word is "fully completed" when all participating exercise scores are `> 0`.
   - `TieredSnapshotEntry(BaseModel)` with fields: `source_word_id: int`, `target_word_id: int`, `pair: WordPair`, `scores: dict[str, int]`, `in_repeat_mode: bool`. This is the remote snapshot shape used by the cache for rebuilds.

2. **Create `packages/core/src/nl_processing/core/tiered_ports.py`**:
   - `TieredCandidateProvider(Protocol)` -- `@runtime_checkable`, with method `async def get_tiered_candidates(self) -> list[TieredCandidate]`.
   - `RemoteTieredSyncPort(Protocol)` -- `@runtime_checkable`, with methods:
     - `async def export_tiered_snapshot(self) -> list[TieredSnapshotEntry]`
     - `async def apply_tiered_result(self, *, event_id: str, source_word_id: int, exercise_type: str, delta: int) -> None`

3. **Create `packages/core/tests/unit/core/test_tiered_models.py`**:
   - Test `TieredCandidate` construction with valid data.
   - Test `TieredExerciseSelection` construction.
   - Test `TieredProgressSummary` construction with boundary values (0 words, full completion).
   - Test `TieredSnapshotEntry` construction.
   - Test pydantic validation rejects missing required fields.

4. **Create `packages/core/tests/unit/core/test_tiered_ports.py`**:
   - Define a minimal mock class implementing `TieredCandidateProvider` and verify `isinstance()` check passes.
   - Define a minimal mock class implementing `RemoteTieredSyncPort` and verify `isinstance()` check passes.
   - Verify that a non-conforming class fails the `isinstance()` check.

5. **Run `make -C packages/core check`** and verify all tests pass, linters pass, no new warnings.

## Production safety constraints (mandatory)

- No database operations in this task. Core package is pure Python models and protocols.
- No external service dependencies.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: extends existing `core` package patterns (BaseModel subclasses, Protocol definitions).
- **Correct file locations**: follows existing `core/models.py` and `core/ports.py` pattern but in separate files to respect 200-line limit.
- **No regressions**: existing `test_models.py`, `test_prompts.py`, `test_exceptions.py` must continue to pass unchanged.

## Error handling + correctness rules (mandatory)

- No error handling needed in pure data models and protocols.
- Pydantic validation provides automatic field validation; do not add custom validators unless spec requires them.

## Zero legacy tolerance rule (mandatory)

- No legacy code to remove. This is a purely additive task.
- Do not add unused fields or methods "for later."

## Acceptance criteria (testable)

1. `TieredCandidate` can be instantiated with all required fields and serializes correctly.
2. `TieredExerciseSelection` can be instantiated and includes the `exercise_type` field.
3. `TieredProgressSummary` correctly holds `total_words`, `fully_completed_words`, and `completion_ratio`.
4. `TieredSnapshotEntry` includes `source_word_id`, `target_word_id`, `pair`, `scores`, and `in_repeat_mode`.
5. `TieredCandidateProvider` is `@runtime_checkable` and correctly identifies conforming classes via `isinstance()`.
6. `RemoteTieredSyncPort` is `@runtime_checkable` and correctly identifies conforming classes via `isinstance()`.
7. Existing `core` tests pass unchanged.
8. `make -C packages/core check` passes (lint, format, unit tests).

## Verification / quality gates

- [ ] Unit tests added for all four new models
- [ ] Protocol conformance tests added for both new protocols
- [ ] Linters/formatters pass (`ruff format`, `ruff check`, `pylint` module-lines check)
- [ ] No new warnings introduced
- [ ] Existing core tests unchanged and passing
- [ ] All new files under 200 lines

## Edge cases

- `TieredProgressSummary` with `total_words=0` must produce `completion_ratio=0.0` (not division by zero).
- `TieredCandidate` with empty `scores` dict is technically valid at the model level (provider contract ensures this doesn't happen at runtime, but the model shouldn't crash).

## Notes / risks

- **Risk**: New files in `core` could affect vulture's dead-code analysis since nothing uses these models yet.
  - **Mitigation**: The vulture whitelist (`vulture_whitelist.py`) may need entries, or the developer should verify that `make check` at root level still passes. However, per task scope, only `make -C packages/core check` is required. Full `make check` runs at sprint DoD.
