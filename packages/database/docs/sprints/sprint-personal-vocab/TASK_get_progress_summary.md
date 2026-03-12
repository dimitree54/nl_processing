---
Task ID: `T4`
Title: `Implement get_progress_summary() on ExerciseProgressStore (FR-8)`
Sprint: `2026-03-12_personal-vocab`
Module: `database`
Depends on: `T2`
Parallelizable: `yes, with T3 and T5`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Expose `get_progress_summary()` on `ExerciseProgressStore` that reports, for each configured exercise type, the total translated personal-word count plus the negative-word count, ratio, and percentage. This fulfills FR-8 and DEC-7.

## Context (contract mapping)

- Requirements: `docs/module-spec.md` — FR-8 (exercise-progress summary: total, negative count/ratio/percentage), DEC-7 (negative_words / total_words * 100 per exercise type)
- Module spec: `docs/module-spec.md` — IF-2 (ExerciseProgressStore.get_progress_summary()), AC-5

## Preconditions

- T2 complete: `_get_rows_with_scores()` helper works with enriched rows and returns score data per exercise type.
- `exercise_progress.py` is at ≤200 lines (T2 may have already decomposed it).

## Non-goals

- Modifying `list_personal_words()` (T3 handles that).
- Modifying delete functionality (T5 handles that).
- Calculating averages or aggregates beyond negative-word percentage.
- Handling untranslated words in the summary (only translated entries are counted, consistent with existing read behavior).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `src/nl_processing/database/models.py` — add `ExerciseProgressSummary` model
- `src/nl_processing/database/exercise_progress.py` — add `get_progress_summary()` method (or extracted module if T2 decomposed)
- `tests/unit/database/test_exercise_progress.py` — add unit tests
- `tests/integration/database/` — add integration test if appropriate
- `tests/e2e/database/` — add e2e test

**FORBIDDEN — this task must NEVER touch:**
- `packages/core/` or any core package file
- Any other module's code or tests

**Test scope:**
- Tests go in: `tests/unit/database/`, `tests/integration/database/`, `tests/e2e/database/`
- Test command: `make check`

## Touched surface (expected files / modules)

- `src/nl_processing/database/models.py` — `ExerciseProgressSummary` model
- `src/nl_processing/database/exercise_progress.py` — `get_progress_summary()` method
- `tests/unit/database/test_exercise_progress.py` — unit tests for progress summary

## Dependencies and sequencing notes

- Depends on T2 because it needs the `_get_rows_with_scores()` helper with enriched row data.
- Parallel with T3 (touches `service.py` and `test_service.py`) and T5 (touches backend files) — minimal file contention.
- T4 primarily touches `exercise_progress.py` and `test_exercise_progress.py`.

## Third-party / library research (mandatory for any external dependency)

No new external dependencies. Uses:
- `pydantic.BaseModel` — for `ExerciseProgressSummary`
- Existing `_get_rows_with_scores()` from `ExerciseProgressStore`

## Implementation steps (developer-facing)

1. **Create `ExerciseProgressSummary` model in `models.py`**:
   ```python
   class ExerciseProgressSummary(BaseModel):
       """Per-exercise-type progress report (FR-8, DEC-7)."""
       total_words: int
       negative_words: int
       negative_ratio: float
       negative_percentage: float
   ```
   - `models.py` stays well under 200 lines.

2. **Add `get_progress_summary()` to `ExerciseProgressStore`**:
   - Method signature: `async def get_progress_summary(self) -> dict[str, ExerciseProgressSummary]:`
   - Implementation:
     1. Call `self._get_rows_with_scores()` to get `(rows, scores_by_word)`.
     2. If no rows, return `{et: ExerciseProgressSummary(total_words=0, negative_words=0, negative_ratio=0.0, negative_percentage=0.0) for et in self._exercise_types}`.
     3. For each exercise type:
        - `total_words = len(rows)` (all translated personal words).
        - Count `negative_words`: iterate source_word_ids, get score from `scores_by_word.get(wid, {}).get(exercise_type, 0)`, count where `score < 0`. Missing scores default to `0` per FR-8 ("Missing scores count as 0, not negative").
        - `negative_ratio = negative_words / total_words` if `total_words > 0` else `0.0`.
        - `negative_percentage = negative_ratio * 100`.
     4. Return `{exercise_type: ExerciseProgressSummary(...) for exercise_type in self._exercise_types}`.
   - **Line count**: `exercise_progress.py` is at ~195-198 after T2. Adding `get_progress_summary()` (~15-20 lines) will exceed 200. **The developer must decompose.**
   - **Decomposition strategy**: Extract `get_progress_summary()` into a new file `src/nl_processing/database/progress_summary.py` as a standalone async function, then call it from `ExerciseProgressStore.get_progress_summary()` as a thin wrapper. OR if T2 already decomposed the file, there may be room. The developer must check line counts and decompose accordingly.

3. **Write unit tests in `test_exercise_progress.py`** (or a new `test_progress_summary.py` if the test file is near 200 lines):
   - `test_get_progress_summary_all_positive`: Seed 3 words, all scores ≥ 0 → `negative_words=0`, `negative_percentage=0.0`.
   - `test_get_progress_summary_some_negative`: Seed 3 words, 1 with negative score → `negative_words=1`, `negative_percentage≈33.33`.
   - `test_get_progress_summary_all_negative`: All scores < 0 → `negative_words=total_words`, `negative_percentage=100.0`.
   - `test_get_progress_summary_missing_scores_not_negative`: No scores at all → all default to 0 → `negative_words=0`.
   - `test_get_progress_summary_empty_vocabulary`: No words → `total_words=0`, `negative_words=0`, `negative_percentage=0.0`.
   - `test_get_progress_summary_multiple_exercise_types`: Two exercise types → dict has both keys with independent calculations.
   - **Line count for `test_exercise_progress.py`**: Currently 163 lines. Adding ~50-60 lines → ~223. **Must decompose**: create `tests/unit/database/test_progress_summary.py` for the new tests.

4. **Write e2e test** (in `tests/e2e/database/test_exercise_progress.py` or new file):
   - Add words, wait for translations, set some scores to negative, call `get_progress_summary()`.
   - Assert summary counts and percentages.

5. **Run `make check`** and verify all tests pass, all files under 200 lines.

## Production safety constraints (mandatory)

- **Database operations**: Read-only queries against test DB. No writes beyond test data setup.
- **Resource isolation**: UUID-based user isolation. No port/file conflicts.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Reuses `_get_rows_with_scores()` — no new backend queries needed.
- **Correct libraries only**: `pydantic` — already used.
- **Correct file locations**: Model in `models.py`, logic in `exercise_progress.py` or extracted file.
- **No regressions**: New method; no changes to existing methods.
- **File decomposition required**: Both `exercise_progress.py` and `test_exercise_progress.py` will need decomposition.

## Error handling + correctness rules (mandatory)

- Division by zero when `total_words == 0`: Return `0.0` for ratio and percentage. Do not raise.
- Missing scores count as `0`, not negative (FR-8 explicit requirement). Do not count them as negative.
- No silenced errors. Backend failures from `_get_rows_with_scores()` propagate naturally.

## Zero legacy tolerance rule (mandatory)

- No dead code introduced. If `get_progress_summary()` is extracted into a separate module, the wrapper on `ExerciseProgressStore` stays thin and delegates.
- No old computation paths superseded.

## Acceptance criteria (testable)

1. `ExerciseProgressSummary` model exists in `database.models` with: `total_words: int`, `negative_words: int`, `negative_ratio: float`, `negative_percentage: float`.
2. `ExerciseProgressStore.get_progress_summary()` returns `dict[str, ExerciseProgressSummary]` keyed by exercise type.
3. For each exercise type, `total_words` equals the count of translated personal words.
4. `negative_words` counts only words where `score < 0` for that exercise type.
5. Missing scores (not in score table) count as `0`, not negative.
6. `negative_ratio = negative_words / total_words` (or `0.0` if `total_words == 0`).
7. `negative_percentage = negative_ratio * 100` (DEC-7).
8. Empty vocabulary returns all zeros.
9. Multiple exercise types report independent summaries.
10. Unit tests cover: all positive, some negative, all negative, missing scores, empty vocab, multiple exercise types.
11. E2e test confirms real DB flow.
12. `exercise_progress.py` ≤ 200 lines (decomposition done if needed).
13. `make check` is green.

## Verification / quality gates

- [ ] Unit tests added for all progress summary scenarios
- [ ] E2e test added
- [ ] `make check` green
- [ ] No new warnings
- [ ] All source files ≤ 200 lines
- [ ] All test files ≤ 200 lines
- [ ] Negative-path test: empty vocabulary returns zeros without error

## Edge cases

- Zero total words → ratio and percentage are `0.0`, not division-by-zero.
- All words have `score == 0` (either explicit or default) → `negative_words == 0`.
- Word with `score == 0` → NOT negative (only `< 0` counts).
- Very large vocabulary → no special handling needed (standard SQL + Python).
- Score of exactly `-1` → counts as negative.

## Notes / risks

- **Risk**: `exercise_progress.py` will exceed 200 lines.
  - **Mitigation**: Extract `get_progress_summary()` logic into `progress_summary.py` or ensure T2's decomposition left enough room.
- **Risk**: `test_exercise_progress.py` will exceed 200 lines.
  - **Mitigation**: Create `tests/unit/database/test_progress_summary.py` for new tests.
- **DEC-7 precision**: Use standard Python float arithmetic for `negative_words / total_words * 100`. No special rounding required by the spec.
