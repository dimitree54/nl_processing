---
Task ID: T4
Title: Implement `TieredExerciseSampler` in `sampling`
Sprint: `2026-03-14_tiered-mixed-exercise`
Module: sampling
Depends on: T1
Parallelizable: yes, with T2 and T3
---

## Goal / value

After this task, the `sampling` package exposes a fully tested `TieredExerciseSampler` that performs weighted random sampling over tiered candidates, selects the correct exercise for each sampled word based on ordered complexity and repeat-mode, and returns `TieredExerciseSelection` results. The sampler is stateless -- it reads from any `TieredCandidateProvider` and never mutates scores or repeat-state. All existing `WordSampler` behavior remains untouched.

## Context (contract mapping)

- Spec: `packages/sampling/docs/module-spec.md` Section 5 (TFR-1..9, TBR-1..5, TIF-1..4, TDEC-1..4, TAC-1..4, TA-1)
- Core tiered models from T1: `TieredCandidate`, `TieredExerciseSelection`
- Core tiered ports from T1: `TieredCandidateProvider`
- Existing patterns: `service.py` (`WordSampler`), `tests/unit/sampling/conftest.py`

## Preconditions

- T1 completed: `core` has `TieredCandidate`, `TieredExerciseSelection`, `TieredCandidateProvider`.
- `make -C packages/sampling check` passes before starting.

## Non-goals

- Modifying `WordSampler` or `sample_adversarial`.
- Implementing repeat-state transitions or score mutations (owned by persistence).
- Implementing a tiered adversarial sampler (not in spec).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**

- `packages/sampling/src/nl_processing/sampling/` -- add tiered sampler module
- `packages/sampling/tests/` -- add tiered tests

**FORBIDDEN -- this task must NEVER touch:**

- `packages/core/`, `packages/database/`, `packages/database_cache/`
- Existing `service.py` in sampling
- `docs/`, `Makefile`, `pyproject.toml`, `ruff.toml`

**Test scope:**

- Tests go in: `packages/sampling/tests/unit/sampling/`
- Test command: `make -C packages/sampling check`
- NEVER run the full test suite or tests from other modules

## Touched surface (expected files / modules)

- NEW: `packages/sampling/src/nl_processing/sampling/tiered_sampler.py` -- `TieredExerciseSampler` class
- NEW: `packages/sampling/tests/unit/sampling/test_tiered_sampler.py` -- unit tests for tiered sampler
- NEW: `packages/sampling/tests/unit/sampling/test_tiered_exercise_selection.py` -- unit tests for exercise selection logic

## Dependencies and sequencing notes

- Depends only on T1 (core DTOs and protocol). Does NOT depend on T2 or T3.
- Can run fully in parallel with T2 (database) and T3 (cache).
- Uses only the `TieredCandidateProvider` protocol -- tests use mock providers, no real database or cache needed.

## Third-party / library research (mandatory for any external dependency)

No new third-party dependencies. Uses existing:

- **Python `random` module** (already used in `service.py` for weighted sampling)

## Implementation steps (developer-facing)

1. **Create `packages/sampling/src/nl_processing/sampling/tiered_sampler.py`** with `TieredExerciseSampler`:
   - Constructor: `__init__(self, *, user_id: str, source_language: Language, target_language: Language, mode_slug: str, exercise_types: list[str], finished_word_weight: float = 0.01, tiered_store: TieredCandidateProvider | None = None)`.
     - Validate `exercise_types` is non-empty.
     - Validate `finished_word_weight` is in `(0, 1]` (TBR-3).
     - Validate `mode_slug` is non-empty.
     - Store `exercise_types` as-is -- must never reorder (TBR-1).
     - If `tiered_store` is None, construct `TieredExerciseProgressStore` as default (following `WordSampler`'s pattern of defaulting to `ExerciseProgressStore`).
   - `async def sample(self, limit: int) -> list[TieredExerciseSelection]`:
     - Return `[]` if `limit <= 0`.
     - Fetch candidates via `tiered_store.get_tiered_candidates()`.
     - Return `[]` if no candidates.
     - Compute weight for each candidate:
       - If any participating exercise score is `<= 0` -> weight `1.0` (TFR-4).
       - If all participating exercise scores are `> 0` -> weight `finished_word_weight` (TFR-5).
     - Select `min(limit, len(candidates))` candidates via weighted random without replacement (TBR-2). Follow the same selection loop pattern as `WordSampler.sample()`.
     - For each selected candidate, determine the exercise:
       - **Normal mode** (not in repeat): choose the most complex (last in ordered list) exercise whose score is `<= 0` (TFR-6).
       - **Repeat mode** (in repeat): choose the most complex (last in ordered list) exercise whose score is `> 0` (TFR-7).
       - **Fully finished, not in repeat** (all scores > 0, review case per TA-1): show the most complex exercise (last in list).
       - **Invalid repeat mode** (in repeat but no positive score): raise `ValueError` per TBR-5. The sampler must not silently fall back.
     - Return `list[TieredExerciseSelection]`.
   - Private helper `_compute_weight(self, candidate: TieredCandidate) -> float`.
   - Private helper `_select_exercise(self, candidate: TieredCandidate) -> str`.

2. **Create `packages/sampling/tests/unit/sampling/test_tiered_sampler.py`** with:
   - **Constructor validation tests:**
     - Empty `exercise_types` raises `ValueError`.
     - `finished_word_weight=0` raises `ValueError`.
     - `finished_word_weight=-0.5` raises `ValueError`.
     - `finished_word_weight=1.0` is valid.
     - Empty `mode_slug` raises `ValueError`.
   - **Mock provider setup:** Create a `MockTieredCandidateProvider` class implementing `TieredCandidateProvider`. Use it in all tests.
   - **Sampling behavior tests:**
     - `sample(0)` returns `[]`.
     - `sample(-1)` returns `[]`.
     - `sample(n)` returns exactly `n` items when enough candidates exist.
     - `sample(n)` returns all candidates when `n > len(candidates)`.
     - No duplicates in results (without-replacement).
     - Empty candidates returns `[]`.
   - **Weighting tests:**
     - Statistical test: unfinished words (some score <= 0) sampled much more often than fully finished words (all scores > 0). Similar structure to `test_sample_statistical_weighting` in existing tests.
   - **Protocol conformance test:** `MockTieredCandidateProvider` satisfies `isinstance(..., TieredCandidateProvider)`.

3. **Create `packages/sampling/tests/unit/sampling/test_tiered_exercise_selection.py`** with:
   - **Normal mode exercise selection:**
     - Word with scores `{"flashcard": 0, "fill_gap": 0}` (exercises ordered lowest to highest) -> selects `fill_gap` (most complex with score <= 0) (TFR-6).
     - Word with scores `{"flashcard": 2, "fill_gap": 0}` -> selects `fill_gap` (only non-positive).
     - Word with scores `{"flashcard": 0, "fill_gap": 3}` -> selects `flashcard` (most complex with score <= 0, which is flashcard since fill_gap is positive).
   - **Repeat mode exercise selection:**
     - Word in repeat with scores `{"flashcard": 2, "fill_gap": -1}` -> selects `flashcard` (most complex positive) (TFR-7).
     - Word in repeat with scores `{"flashcard": 1, "fill_gap": 3}` -> selects `fill_gap` (most complex positive).
   - **Fully finished review (TA-1):**
     - Word with all positive scores, not in repeat -> selects the most complex exercise (last in list).
   - **Invalid repeat state (TBR-5):**
     - Word in repeat with all non-positive scores -> raises `ValueError`.
   - **Three-exercise tier tests:**
     - Test with `["flashcard", "fill_gap", "translation"]` to verify correct tier selection with 3 levels.

4. **Run `make -C packages/sampling check`** and verify all tests pass.

## Production safety constraints (mandatory)

- No database or external service operations in this task. The sampler is stateless and uses only mock providers in tests.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follow `WordSampler` patterns (constructor validation, weighted selection loop, mock store injection).
- **Correct file locations**: `tiered_sampler.py` follows the existing `service.py` location pattern inside `sampling/`.
- **No regressions**: Existing `test_sampling_weights.py` and `test_sampling_adversarial.py` must pass unchanged (TAC-1).

## Error handling + correctness rules (mandatory)

- Invalid repeat state (TBR-5): in_repeat=True with no positive score must raise `ValueError`, not fall back silently.
- Empty exercise_types, bad weight, empty mode_slug: all raise `ValueError` at construction time.
- Do not catch or swallow errors from the provider -- let them propagate.

## Zero legacy tolerance rule (mandatory)

- No legacy code to remove. Purely additive.
- Do not create placeholder adversarial methods or unused weight strategies.

## Acceptance criteria (testable)

1. `TieredExerciseSampler` raises `ValueError` for invalid constructor params.
2. Tiered sampling returns unique `TieredExerciseSelection` items including both the word pair and the selected exercise (TAC-2).
3. Unfinished words sample with weight 1.0, fully finished words with `finished_word_weight` (TAC-3).
4. Normal-mode selections choose the most complex non-positive exercise (TAC-4).
5. Repeat-mode selections choose the most complex positive exercise (TAC-4).
6. Fully finished words in normal mode show the most complex exercise (TA-1).
7. Invalid repeat state raises `ValueError` (TBR-5).
8. Sampling is without-replacement within one call (TBR-2).
9. Exercise order is never internally reordered (TBR-1).
10. Existing `WordSampler` tests pass unchanged (TFR-9, TAC-1).
11. `make -C packages/sampling check` passes.

## Verification / quality gates

- [ ] Constructor validation unit tests
- [ ] Sampling behavior unit tests (count, no-dup, empty, boundary)
- [ ] Statistical weighting test
- [ ] Exercise selection unit tests (normal, repeat, review, invalid, 3-tier)
- [ ] Protocol conformance test for mock provider
- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] All files under 200 lines
- [ ] Negative-path tests: invalid repeat state, bad constructor params

## Edge cases

- Only one candidate: `sample(1)` returns that candidate with correct exercise.
- All candidates fully finished: all get `finished_word_weight`, sampling still works.
- All candidates in repeat mode: each gets repeat-mode exercise selection.
- Single exercise type: exercise selection always returns that type (both normal and repeat mode degenerate to the same exercise).
- Word with a single exercise at score 0, not in repeat: selects that exercise (it's both the most complex and the non-positive one).

## Notes / risks

- **Risk**: TA-1 is a "temporary working assumption" -- finished-word review exercise may change later.
  - **Mitigation**: The implementation is straightforward (most complex exercise for review). If the assumption changes, only `_select_exercise` needs updating.

- **Risk**: The `_select_exercise` logic has distinct branches for normal/repeat/review. Off-by-one in the ordered list traversal could select the wrong tier.
  - **Mitigation**: Dedicated test cases for 2-exercise and 3-exercise configurations with known expected outcomes ensure correctness.
