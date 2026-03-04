---
Task ID: `T13`
Title: `Unit tests for WordSampler`
Sprint: `2026-03-04_database-and-sampling`
Module: `sampling`
Depends on: `T12`
Parallelizable: `yes, with T10 and T11`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Unit tests validate WordSampler logic with a mocked ExerciseProgressStore. No real database connections — pure logic testing for weight computation, sampling behavior, adversarial filtering, and input validation.

## Context (contract mapping)

- Requirements: `nl_processing/sampling/docs/prd_sampling.md` — all FRs tested
- Architecture: `nl_processing/sampling/docs/architecture_sampling.md` — Test Strategy: Unit tests

## Preconditions

- T12 complete (WordSampler implementation)

## Non-goals

- No real database connections
- No integration testing (that's T14)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**

- `tests/unit/sampling/` — create directory + test files
- `tests/unit/sampling/__init__.py` — create (empty)
- `tests/unit/sampling/conftest.py` — create (mock fixtures)
- `tests/unit/sampling/test_sampler.py` — WordSampler unit tests

**FORBIDDEN — this task must NEVER touch:**

- Any module source code
- Tests for other modules

**Test scope:**

- Tests go in: `tests/unit/sampling/`
- Test command: `make check` (runs `uv run pytest -n auto tests/unit` which includes these)

## Touched surface (expected files / modules)

- `tests/unit/sampling/__init__.py` (new, empty)
- `tests/unit/sampling/conftest.py` (new)
- `tests/unit/sampling/test_sampler.py` (new)

## Dependencies and sequencing notes

- Depends on T12 (WordSampler must exist)
- Can run in parallel with T10, T11, T14

## Third-party / library research (mandatory for any external dependency)

- **Library**: pytest + pytest-asyncio (already installed)
- No new dependencies

## Implementation steps (developer-facing)

1. **Create `tests/unit/sampling/` directory with `__init__.py` (empty).**

2. **Create `tests/unit/sampling/conftest.py`:**
   - Define a `MockExerciseProgressStore` that returns configurable `list[ScoredWordPair]` from `get_word_pairs_with_scores`
   - Define helper functions to create test `ScoredWordPair` instances with known scores
   - Define a fixture that creates a `WordSampler` with the mock store injected (monkeypatch the internal `_progress_store` attribute)

3. **Create `tests/unit/sampling/test_sampler.py`:**

   **Constructor validation tests:**
   - Test: empty `exercise_types` raises `ValueError`
   - Test: `positive_balance_weight=0` raises `ValueError`
   - Test: `positive_balance_weight=-0.5` raises `ValueError`
   - Test: `positive_balance_weight=1.0` is valid
   - Test: `positive_balance_weight=0.01` is valid (default)

   **Weight computation tests:**
   - Test: word with all positive scores → weight = `positive_balance_weight`
   - Test: word with any non-positive score → weight = 1.0
   - Test: word with mixed scores across exercises → min_score determines weight
   - Test: word with missing scores (treated as 0) → weight = 1.0

   **Sampling behavior tests:**
   - Test: `sample(0)` returns `[]`
   - Test: `sample(-1)` returns `[]`
   - Test: `sample(limit)` returns at most `limit` items
   - Test: `sample(limit)` where limit > candidates → returns all candidates
   - Test: `sample` returns no duplicates (without replacement)
   - Test: empty candidate set → returns `[]`
   - Test: statistical sanity check — sample 1000 times with a mix of positive/non-positive scored words, verify non-positive words appear more frequently (rough distribution check, not exact)

   **Adversarial sampling tests:**
   - Test: `sample_adversarial` returns only same-POS words
   - Test: `sample_adversarial` excludes the source word itself
   - Test: `sample_adversarial` with `limit=0` returns `[]`
   - Test: `sample_adversarial` with no matching POS returns `[]`
   - Test: `sample_adversarial` with fewer candidates than limit → returns all available
   - Test: `sample_adversarial` with wrong language raises `ValueError`
   - Test: `sample_adversarial` returns no duplicates

4. **200-line limit**: If `test_sampler.py` exceeds 200 lines, split into `test_sampling_weights.py` and `test_sampling_adversarial.py`.

5. Run `make check`.

## Production safety constraints (mandatory)

- **Database operations**: None — all mocked.
- **Resource isolation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follows existing test patterns.
- **No regressions**: New tests only.

## Error handling + correctness rules (mandatory)

- Test all error paths (ValueError for invalid params, ValueError for wrong language).
- No `pytest.skip`.
- Statistical tests should be robust (large sample size, generous tolerance).

## Zero legacy tolerance rule (mandatory)

- No old test files.

## Acceptance criteria (testable)

1. `tests/unit/sampling/` directory exists with conftest and test files.
2. At least 18 unit tests covering constructor validation, weight computation, sampling behavior, and adversarial sampling.
3. All tests use mocked ExerciseProgressStore — no real database.
4. Statistical sanity check confirms weighting behavior.
5. All error paths tested.
6. All test files under 200 lines.
7. `make check` passes.

## Verification / quality gates

- [ ] Test directory created with conftest
- [ ] MockExerciseProgressStore returns configurable data
- [ ] 18+ unit tests pass
- [ ] No real DB connections
- [ ] Statistical test passes
- [ ] All files under 200 lines
- [ ] `make check` passes

## Edge cases

- Statistical test may be flaky — use large sample size (1000+ iterations) and generous tolerance (e.g., non-positive words should be sampled >5x more than positive ones, given default 0.01 weight).
- `random.seed` can be set in tests for deterministic behavior where needed (but statistical test should work without seeding).

## Notes / risks

- **Risk**: Statistical test flakiness.
  - **Mitigation**: Use `random.seed(42)` for deterministic tests where possible. For the distribution test, use a large sample size and wide tolerance.
