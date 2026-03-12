---
Task ID: `T4`
Title: `Implement get_progress_summary() from cached data`
Sprint: `2026-03-12_cache-personal-vocab`
Module: `database_cache`
Depends on: `T3`
Parallelizable: no
---

## Goal / value

`DatabaseCacheService.get_progress_summary()` returns `dict[str, ExerciseProgressSummary]` computed entirely from local cached data. Each entry reports `total_words`, `negative_words`, `negative_ratio`, and `negative_percentage` for one exercise type. Per DEC-7, the summary derives from the same cached personal-vocabulary record set used by `list_personal_words()`, ensuring the denominator matches the visible word list.

## Context (contract mapping)

- Requirements: `docs/module-spec.md` — FR-8, DEC-7, AC-5
- Module spec: `docs/module-spec.md` — IF-1, QA-5
- Related models: `database.models.ExerciseProgressSummary` (total_words, negative_words, negative_ratio, negative_percentage)
- Related helper: `database._progress_helpers.compute_progress_summary()` — reference implementation

## Preconditions

- T3 (list_personal_words) is complete — the data retrieval path for scored word pairs is established
- The `get_cached_word_pairs_with_scores()` method on `LocalStore` returns rows with `score_{exercise_type}` fields

## Non-goals

- Implementing delete APIs (that's T5)
- Modifying `compute_progress_summary()` in the `database` package
- Supporting untranslated word counts (only translated entries in the cache)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `src/nl_processing/database_cache/` — module source code
- `tests/unit/database_cache/` — unit tests

**FORBIDDEN — this task must NEVER touch:**
- `src/nl_processing/core/` or any `core` package file
- `src/nl_processing/database/` or any `database` package file
- Any other module's code or tests

**Test scope:**
- Tests go in: `tests/unit/database_cache/`
- Test command: `uv run pytest tests/unit/database_cache/ -x -v`
- NEVER run the full test suite or tests from other modules

## Touched surface (expected files / modules)

- `src/nl_processing/database_cache/service.py` — add `get_progress_summary()` method (~10 lines)
- `src/nl_processing/database_cache/_service_helpers.py` — add `compute_local_progress_summary()` function (~25 lines)
- `tests/unit/database_cache/test_service.py` — add tests for `get_progress_summary()`

## Dependencies and sequencing notes

- Depends on T3 because the summary computation uses the same `get_cached_word_pairs_with_scores()` data path.
- DEC-7 explicitly requires that the summary denominators match the `list_personal_words()` count. Using the same underlying query guarantees this.
- File contention with T5 on `service.py` — serialize.

## Third-party / library research (mandatory for any external dependency)

No new third-party libraries. Uses:
- `nl_processing.database.models.ExerciseProgressSummary` — Pydantic model with fields: `total_words: int`, `negative_words: int`, `negative_ratio: float`, `negative_percentage: float`.

**Why not reuse `compute_progress_summary()` from `database._progress_helpers`?**

The helper expects rows with a `source_id` key (from `database` backend row format), but cached rows use `source_word_id`. Additionally, it reads scores from a `scores_by_word` dict keyed by `source_id`, while cached rows have `score_{exercise_type}` flattened into the row dict. The math is trivial (~15 lines) and reimplementing it locally avoids fragile coupling to `database`'s internal row key names.

The math:
```
total_words = len(rows)
negative_words = count of rows where score < 0 for this exercise type
negative_ratio = negative_words / total_words  (or 0.0 if total_words == 0)
negative_percentage = negative_ratio * 100
```

## Implementation steps (developer-facing)

### Step 1: Add `compute_local_progress_summary()` in `_service_helpers.py`

```python
from nl_processing.database.models import ExerciseProgressSummary

def compute_local_progress_summary(
    rows: list[dict[str, str | int]],
    exercise_types: list[str],
) -> dict[str, ExerciseProgressSummary]:
    """Compute progress summary from cached rows with flattened score fields."""
    total_words = len(rows)
    if total_words == 0:
        return {
            et: ExerciseProgressSummary(
                total_words=0,
                negative_words=0,
                negative_ratio=0.0,
                negative_percentage=0.0,
            )
            for et in exercise_types
        }
    result: dict[str, ExerciseProgressSummary] = {}
    for et in exercise_types:
        score_key = f"score_{et}"
        negative_words = sum(1 for r in rows if int(r.get(score_key, 0)) < 0)
        negative_ratio = negative_words / total_words
        result[et] = ExerciseProgressSummary(
            total_words=total_words,
            negative_words=negative_words,
            negative_ratio=negative_ratio,
            negative_percentage=negative_ratio * 100,
        )
    return result
```

### Step 2: Add `get_progress_summary()` to `service.py`

```python
async def get_progress_summary(self) -> dict[str, ExerciseProgressSummary]:
    """Return per-exercise progress stats from cached data (FR-8, DEC-7)."""
    self._ensure_ready()
    assert self._local is not None
    rows = await self._local.get_cached_word_pairs_with_scores(self._exercise_types)
    return compute_local_progress_summary(rows, self._exercise_types)
```

Add the necessary import for `compute_local_progress_summary` and `ExerciseProgressSummary`.

### Step 3: Add unit tests in `test_service.py`

1. **`test_get_progress_summary_all_zero`** — with 2 words both at score 0, verify `negative_words=0`, `negative_ratio=0.0`, `negative_percentage=0.0`, `total_words=2` for each exercise type.

2. **`test_get_progress_summary_with_negative_scores`** — record exercise results with `delta=-1` for one word, verify `negative_words=1`, `total_words=2`, `negative_ratio=0.5`, `negative_percentage=50.0`.

3. **`test_get_progress_summary_empty_cache`** — after init with an empty snapshot (no words), verify `total_words=0`, `negative_words=0`, `negative_ratio=0.0`, `negative_percentage=0.0`.

4. **`test_get_progress_summary_before_init_raises`** — verify `CacheNotReadyError` when called before `init()`.

5. **`test_get_progress_summary_matches_list_personal_words_count`** — DEC-7 verification: call both `list_personal_words()` and `get_progress_summary()`, verify `total_words == len(list_personal_words())`.

### Step 4: Run tests and verify line counts

1. `uv run pytest tests/unit/database_cache/ -x -v`
2. Verify `service.py` is still under 200 lines (~5 lines added).
3. Verify `_service_helpers.py` is still under 200 lines (~25 lines added).

## Production safety constraints (mandatory)

- **Database operations**: All reads/writes target testing/development databases only. No production data accessed.
- **No schema change**: Reads from existing cached data. No DDL modifications.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Reuses `get_cached_word_pairs_with_scores()` — same data path as `list_personal_words()` (DEC-7 compliance).
- **No reinvention**: The math mirrors `compute_progress_summary()` from `database._progress_helpers` but adapted for the cached row shape. Not a duplication — it's a different input format.
- **No regressions**: Existing tests must pass alongside new tests.

## Error handling + correctness rules (mandatory)

- **Do not silence errors**: Missing score keys in a row should be treated as `0` (per FR-8 spec: "Missing scores count as 0; negative means score < 0").
- **CacheNotReadyError**: `get_progress_summary()` calls `self._ensure_ready()`.
- Division by zero: explicitly handled — if `total_words == 0`, all ratios are `0.0`.

## Zero legacy tolerance rule (mandatory)

After implementing this task:

- `get_progress_summary()` is the canonical local progress summary API.
- No duplicate summary computation exists in the cache module.

## Acceptance criteria (testable)

1. `DatabaseCacheService.get_progress_summary()` exists and returns `dict[str, ExerciseProgressSummary]`.
2. Each key in the returned dict corresponds to one of the configured `exercise_types`.
3. `total_words` matches the number of cached word pairs (i.e., `len(list_personal_words())`).
4. `negative_words` counts only words with `score < 0` for that exercise type.
5. `negative_ratio = negative_words / total_words` (or `0.0` if empty).
6. `negative_percentage = negative_ratio * 100`.
7. Empty cache returns all-zero summaries.
8. Calling before `init()` raises `CacheNotReadyError`.
9. All files remain under 200 lines.

## Verification / quality gates

- [ ] Unit tests added and pass: `uv run pytest tests/unit/database_cache/ -x -v`
- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] Negative-path test: before init raises `CacheNotReadyError`
- [ ] DEC-7 verification test: total_words matches list_personal_words count
- [ ] Line counts verified: all files under 200

## Edge cases

- Empty cache — returns all-zero summaries for each exercise type.
- All scores zero — `negative_words = 0` for all exercise types.
- All scores negative — `negative_words == total_words`, ratio = 1.0, percentage = 100.0.
- Mixed positive/negative — only negative scores count toward `negative_words`.
- Single exercise type — dict has exactly one key.
- Multiple exercise types — one summary per type, each computed independently.

## Notes / risks

- **Risk**: The local `compute_local_progress_summary()` could drift from `compute_progress_summary()` in the `database` package.
  - **Mitigation**: The math is trivial (count negatives / total). Both implementations are tested. The module spec (DEC-7) defines the exact formula. If the remote formula ever changes, the cache formula must be updated to match.
- **Risk**: Line count pressure on `_service_helpers.py` if it grows too much.
  - **Mitigation**: `compute_local_progress_summary()` is ~20 lines. Combined with `row_to_word_pair()` (~10 lines) and `_parse_dt()` (~5 lines) and `row_to_personal_word()` (~15 lines), total is ~50 lines. Well under 200.
