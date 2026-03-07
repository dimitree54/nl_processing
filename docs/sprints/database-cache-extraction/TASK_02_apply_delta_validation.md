---
Task ID: `T2`
Title: `Add delta validation to apply_score_delta`
Sprint: `2026-03-07_database-cache-extraction`
Module: `database`
Depends on: `--`
Parallelizable: `yes, with T1, T4`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Enforce FR32 (`delta` limited to +1 or -1) in `ExerciseProgressStore.apply_score_delta()`. Currently, only `increment()` validates delta; `apply_score_delta()` accepts any integer. After this task, both methods reject invalid deltas consistently.

## Context (contract mapping)

- Requirements: `nl_processing/database/docs/prd_database.md` FR32 -- "delta is limited to +1 or -1."
- Architecture: `nl_processing/database/docs/architecture_database.md` -- "apply_score_delta(event_id, ...)" section.
- Sprint request: Discrepancy 6 -- "`apply_score_delta` doesn't validate delta range."

## Preconditions

- `make check` is green before starting.
- `nl_processing/database/exercise_progress.py` exists with the current `apply_score_delta` implementation (lines 113-141).

## Non-goals

- Fixing the atomicity of `apply_score_delta` (that is T3).
- Changing `increment()` -- it already validates correctly.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `nl_processing/database/exercise_progress.py` -- add delta validation to `apply_score_delta`
- `tests/unit/database/test_exercise_progress.py` -- add unit tests for delta validation in `apply_score_delta`

**FORBIDDEN -- this task must NEVER touch:**
- Any other module's code or tests
- `nl_processing/database/service.py`
- `nl_processing/database/backend/` files
- Integration or e2e tests
- `vulture_whitelist.py`

**Test scope:**
- Verification command: `make check`
- New tests go in: `tests/unit/database/test_exercise_progress.py`

## Touched surface (expected files / modules)

- `nl_processing/database/exercise_progress.py` -- 2 lines added (validation check)
- `tests/unit/database/test_exercise_progress.py` -- 2 new test functions (~20 lines)

## Dependencies and sequencing notes

- No dependencies. Can run in parallel with T1 and T4.
- T3 depends on this task (T3 modifies the same method for atomicity).

## Third-party / library research (mandatory for any external dependency)

N/A -- no new libraries.

## Implementation steps (developer-facing)

1. **Edit `nl_processing/database/exercise_progress.py`**, method `apply_score_delta` (line 113+):
   - Add delta validation immediately after `self._validate_exercise_type(exercise_type)` (line 124):
     ```python
     if delta not in (1, -1):
         msg = f"delta must be +1 or -1, got {delta}"
         raise ValueError(msg)
     ```
   - This matches the exact pattern used in `increment()` (lines 64-66).

2. **Edit `tests/unit/database/test_exercise_progress.py`**, add two new test functions after the existing `apply_score_delta` test section:

   ```python
   @pytest.mark.asyncio
   async def test_apply_score_delta_rejects_zero(progress_store: ExerciseProgressStore) -> None:
       """apply_score_delta raises ValueError when delta is 0."""
       with pytest.raises(ValueError, match="delta must be"):
           await progress_store.apply_score_delta("evt-zero", 1, "flashcard", 0)


   @pytest.mark.asyncio
   async def test_apply_score_delta_rejects_two(progress_store: ExerciseProgressStore) -> None:
       """apply_score_delta raises ValueError when delta is 2."""
       with pytest.raises(ValueError, match="delta must be"):
           await progress_store.apply_score_delta("evt-two", 1, "flashcard", 2)
   ```

3. **Run `make check`** and confirm 100% green.

## Production safety constraints (mandatory)

- **Database operations**: None. Validation happens before any DB call. Only unit tests are affected.
- **Resource isolation**: N/A.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Reuses the exact same validation pattern from `increment()`.
- **Correct libraries only**: N/A.
- **Correct file locations**: Changes are in existing files.
- **No regressions**: The only existing test for `apply_score_delta` (`test_apply_score_delta_applies_once`) uses `delta=1`, which is valid. No regression.

## Error handling + correctness rules (mandatory)

- The `ValueError` is raised before any database operation, ensuring no partial side effects.
- The error message matches the pattern used by `increment()` for consistency.

## Zero legacy tolerance rule (mandatory)

- No legacy code paths remain for unvalidated delta in `apply_score_delta`.

## Acceptance criteria (testable)

1. `await progress_store.apply_score_delta("e", 1, "flashcard", 0)` raises `ValueError`.
2. `await progress_store.apply_score_delta("e", 1, "flashcard", 2)` raises `ValueError`.
3. `await progress_store.apply_score_delta("e", 1, "flashcard", -2)` raises `ValueError`.
4. `await progress_store.apply_score_delta("e", 1, "flashcard", 1)` succeeds (no error).
5. `await progress_store.apply_score_delta("e2", 1, "flashcard", -1)` succeeds (no error).
6. `make check` is 100% green.

## Verification / quality gates

- [ ] `apply_score_delta` raises `ValueError` for delta not in {+1, -1}
- [ ] At least 2 new unit tests verify invalid delta rejection
- [ ] Existing `test_apply_score_delta_applies_once` still passes
- [ ] `make check` passes
- [ ] No new warnings introduced

## Edge cases

- `delta=0`: must raise ValueError.
- `delta=100`: must raise ValueError.
- `delta=-100`: must raise ValueError.
- Validation runs before the `check_event_applied` DB call, so no side effects on invalid input.

## Notes / risks

- **Risk**: None. This is a minimal, well-understood validation addition.
- The validation is placed after `_validate_exercise_type` but before any DB call, matching the `increment()` pattern.
