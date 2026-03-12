---
Task ID: `T3`
Title: `Implement list_personal_words() local read API`
Sprint: `2026-03-12_cache-personal-vocab`
Module: `database_cache`
Depends on: `T2`
Parallelizable: no
---

## Goal / value

`DatabaseCacheService.list_personal_words()` returns `list[PersonalWord]` from local SQLite, including stable IDs, `added_at`, and per-exercise scores. Hot-path callers can read personal vocabulary without a remote round trip. The return shape matches `DatabaseService.list_personal_words()` so callers do not need to branch on data source (BR-5).

## Context (contract mapping)

- Requirements: `docs/module-spec.md` — FR-7, BR-5, CR-3, AC-4
- Module spec: `docs/module-spec.md` — IF-1, DEC-5, DEC-7
- Related models: `database.models.PersonalWord` (pair, source_word_id, target_word_id, added_at, scores)

## Preconditions

- T1 (decompose) is complete — `service.py` has headroom
- T2 (schema + refresh added_at) is complete — `cached_word_pairs` has `added_at` column and `rebuild_snapshot()` stores it

## Non-goals

- Implementing `get_progress_summary()` (that's T4 — but it reuses the same data retrieval path)
- Implementing delete APIs (that's T5)
- Modifying the remote `DatabaseService.list_personal_words()`

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `src/nl_processing/database_cache/` — module source code
- `tests/unit/database_cache/` — unit tests
- `tests/integration/database_cache/` — integration tests

**FORBIDDEN — this task must NEVER touch:**
- `src/nl_processing/core/` or any `core` package file
- `src/nl_processing/database/` or any `database` package file
- Any other module's code or tests

**Test scope:**
- Tests go in: `tests/unit/database_cache/`, `tests/integration/database_cache/`
- Test command: `uv run pytest tests/unit/database_cache/ tests/integration/database_cache/ -x -v`
- NEVER run the full test suite or tests from other modules

## Touched surface (expected files / modules)

- `src/nl_processing/database_cache/service.py` — add `list_personal_words()` method
- `src/nl_processing/database_cache/local_store.py` — add `get_all_cached_word_pairs_with_scores()` method that returns rows including `added_at` and per-exercise scores
- `tests/unit/database_cache/test_service.py` — add tests for `list_personal_words()`
- `tests/unit/database_cache/test_local_store.py` — add test for the new query method
- `tests/integration/database_cache/test_refresh_rebuild.py` — add test that `list_personal_words()` returns correct data after refresh with `added_at`

## Dependencies and sequencing notes

- Depends on T2 because `added_at` must be in the DDL and stored by `rebuild_snapshot()`.
- T4 (progress_summary) depends on this task because DEC-7 says the summary must derive from the same cached record set.
- File contention with T5 (delete) on `service.py` and `local_store.py` — serialize.

## Third-party / library research (mandatory for any external dependency)

No new third-party libraries. Uses:
- `datetime.fromisoformat()` (stdlib) to parse `added_at` from SQLite `TEXT` back to `datetime`.
- `nl_processing.database.models.PersonalWord` — Pydantic model with fields: `pair: WordPair`, `source_word_id: int`, `target_word_id: int`, `added_at: datetime`, `scores: dict[str, int]`.

## Implementation steps (developer-facing)

### Step 1: Add query method to `local_store.py`

Add `get_all_cached_word_pairs_with_scores(self, exercise_types: list[str]) -> list[dict[str, str | int]]`:

This is similar to the existing `get_cached_word_pairs_with_scores()` but **must also include `added_at`** in the returned dicts. The existing method already returns all columns from `cached_word_pairs` plus score fields — verify that `added_at` is included in the `SELECT *` result after T2's DDL change. If it is (it should be since `SELECT *` returns all columns), then the existing `get_cached_word_pairs_with_scores()` can be reused directly. No new `local_store.py` method may be needed — just verify.

**Decision**: Verify that `get_cached_word_pairs_with_scores()` already returns `added_at` in its dicts (since it uses `SELECT * FROM cached_word_pairs`). If yes, no new method is needed on `local_store.py` — the service method just reads `row["added_at"]` from the existing result.

### Step 2: Add `list_personal_words()` to `service.py`

```python
async def list_personal_words(self) -> list[PersonalWord]:
    """Return personal-vocabulary entries from local cache (FR-7)."""
    self._ensure_ready()
    assert self._local is not None
    rows = await self._local.get_cached_word_pairs_with_scores(self._exercise_types)
    return [self._row_to_personal_word(r) for r in rows]
```

### Step 3: Add `_row_to_personal_word()` helper

This should go in `_service_helpers.py` (or as a private method on the service if it needs `self._source_language` / `self._target_language`). Since `row_to_word_pair()` was already extracted in T1:

```python
def row_to_personal_word(
    row: dict[str, str | int],
    source_language: Language,
    target_language: Language,
    exercise_types: list[str],
) -> PersonalWord:
    """Reconstruct a PersonalWord from a cached row dict."""
    pair = row_to_word_pair(row, source_language, target_language)
    added_at_raw = row.get("added_at")
    added_at = (
        datetime.fromisoformat(str(added_at_raw))
        if added_at_raw is not None
        else datetime.now(tz=UTC)
    )
    scores = {et: int(row.get(f"score_{et}", 0)) for et in exercise_types}
    return PersonalWord(
        pair=pair,
        source_word_id=int(row["source_word_id"]),
        target_word_id=int(row["target_word_id"]),
        added_at=added_at,
        scores=scores,
    )
```

### Step 4: Add unit tests in `test_service.py`

1. `test_list_personal_words_returns_personal_word_objects` — verify return type and count.
2. `test_list_personal_words_includes_added_at` — verify `added_at` is a `datetime` and not `None`.
3. `test_list_personal_words_includes_scores` — verify per-exercise scores are present with correct values.
4. `test_list_personal_words_before_init_raises` — verify `CacheNotReadyError` when called before `init()`.

### Step 5: Add unit test in `test_local_store.py`

1. `test_get_cached_word_pairs_with_scores_includes_added_at` — verify that after `rebuild_snapshot()` with 7-element tuples, the returned dicts include `added_at` as a non-null string.

### Step 6: Add integration test in `test_refresh_rebuild.py`

1. `test_list_personal_words_after_refresh_has_added_at` — use a full `CacheSyncer` + mock remote with `EnrichedWordPairSnapshot` including `added_at`, refresh, then verify `list_personal_words()` returns `PersonalWord` objects with correct `added_at` values.

### Step 7: Run tests and verify line counts

1. `uv run pytest tests/unit/database_cache/ -x -v`
2. `uv run pytest tests/integration/database_cache/ -x -v`
3. Verify `service.py` is still under 200 lines after adding `list_personal_words()` (~5 lines) and any helper call.
4. Verify `_service_helpers.py` is still under 200 lines after adding `row_to_personal_word()` (~15 lines).

## Production safety constraints (mandatory)

- **Database operations**: All reads/writes target testing/development databases only. No production data accessed.
- **No schema change**: This task reads from the schema established in T2. No DDL modifications.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Reuses existing `get_cached_word_pairs_with_scores()` for data retrieval. Reuses `row_to_word_pair()` from T1's extraction for WordPair reconstruction.
- **Correct libraries only**: `datetime` (stdlib), `pydantic` (existing).
- **No regressions**: Existing tests must continue to pass alongside new tests.

## Error handling + correctness rules (mandatory)

- **Do not silence errors**: `added_at` must not silently default when it should be present. If `added_at` is `None` in a row after T2 has been applied, that indicates a bug — use `datetime.now(tz=UTC)` as a defensive fallback **only** for backward compatibility with pre-T2 data, and log a warning.
- **CacheNotReadyError**: `list_personal_words()` calls `self._ensure_ready()` — raises if not initialized.
- No empty catch blocks.

## Zero legacy tolerance rule (mandatory)

After implementing this task:

- `list_personal_words()` is the canonical local personal-vocabulary read.
- No duplicate implementation exists.
- If callers previously assembled personal word data manually from `get_words()` + scores, that pattern should be identified and replaced (unlikely in current codebase, but verify).

## Acceptance criteria (testable)

1. `DatabaseCacheService.list_personal_words()` exists and returns `list[PersonalWord]`.
2. Each `PersonalWord` has `pair: WordPair`, `source_word_id: int`, `target_word_id: int`, `added_at: datetime`, `scores: dict[str, int]`.
3. `scores` contains entries for all configured `exercise_types` (missing scores default to `0`).
4. `added_at` matches the value stored during `refresh()` from `EnrichedWordPairSnapshot`.
5. Calling `list_personal_words()` before `init()` raises `CacheNotReadyError`.
6. Unit tests cover return type, field presence, score values, and pre-init guard.
7. Integration test verifies end-to-end: mock remote → refresh → `list_personal_words()` → correct `PersonalWord` objects.
8. All files remain under 200 lines.

## Verification / quality gates

- [ ] Unit tests added and pass: `uv run pytest tests/unit/database_cache/ -x -v`
- [ ] Integration tests added and pass: `uv run pytest tests/integration/database_cache/ -x -v`
- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] Negative-path test: `list_personal_words()` before init raises `CacheNotReadyError`
- [ ] Line counts verified: all files under 200

## Edge cases

- Empty cache (no word pairs) — `list_personal_words()` returns `[]`.
- Word pair with no scores — `scores` dict has all exercise types set to `0`.
- `added_at` stored as `NULL` in SQLite (pre-T2 data or mock without `added_at`) — defensive fallback to `datetime.now(tz=UTC)`.
- Multiple exercise types — scores dict has one entry per configured exercise type.
- `WordPairSnapshot` mock that lacks `added_at` — handled by the `hasattr` guard in T2's `sync.py` changes; results in `NULL` in SQLite.

## Notes / risks

- **Risk**: `PersonalWord` import from `database.models` creates a compile-time dependency on the `database` package.
  - **Mitigation**: This is expected and matches the existing pattern (the cache already imports from `database.exercise_progress`). The `database` package is a declared dependency.
- **Risk**: The `get_cached_word_pairs_with_scores()` method does N+1 queries (one per word per exercise type). For `list_personal_words()` this could be slow with large vocabularies.
  - **Mitigation**: Acceptable for V1 (personal vocabularies are typically <1000 words). Can be optimized with JOINs in a future task if profiling shows a bottleneck.
