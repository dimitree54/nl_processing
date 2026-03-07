---
Task ID: `T9`
Title: `Update MockBackend, unit test fixtures, and all unit tests`
Sprint: `2026-03-07_database-exercise-tables`
Module: `database`
Depends on: `T6, T7, T8`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Update all unit test infrastructure to match the refactored APIs: (1) update `MockBackend` in `conftest.py` to match new `AbstractBackend` signatures (no `exercise_type` param, `exercise_slugs` in `create_tables`, event tracking methods), (2) update the `progress_store` fixture to pass `exercise_types`, (3) rewrite all `ExerciseProgressStore` tests for new `increment(source_word_id: int, ...)` and `get_word_pairs_with_scores()` signatures, and (4) add new tests for `export_remote_snapshot`, `apply_score_delta` idempotency, constructor validation, and exercise_type validation.

## Context (contract mapping)

- Requirements: Sprint request item 6 — "Testing Updates Required"
- Current: `conftest.py` (169 lines), `test_exercise_progress.py` (108 lines), `test_service.py` (160 lines).
- All ExerciseProgressStore tests use old signatures (Word param, exercise_types param on get).
- MockBackend implements old AbstractBackend (with exercise_type param).

## Preconditions

- T5 completed (ExerciseProgressStore refactored).
- T6 completed (cache-support APIs added).
- T7 completed (cached_service marked legacy).
- T8 completed (testing.py updated).

## Non-goals

- Integration or e2e test updates (T10/T11).
- Modifying any source code.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `tests/unit/database/conftest.py` — MockBackend and fixtures
- `tests/unit/database/test_exercise_progress.py` — ExerciseProgressStore tests
- `tests/unit/database/test_service.py` — DatabaseService tests (may need minor updates for `ScoredWordPair.source_word_id`)

**FORBIDDEN — this task must NEVER touch:**
- Any source code files
- Integration or e2e test files
- Any other module's tests

**Test scope:**
- Tests go in: `tests/unit/database/`
- Test command: `uv run pytest tests/unit/database/ -x -v`

## Touched surface (expected files / modules)

- `tests/unit/database/conftest.py`
- `tests/unit/database/test_exercise_progress.py`
- `tests/unit/database/test_service.py`

## Dependencies and sequencing notes

- Depends on T6 (all source code changes complete).
- Depends on T7 (cached_service marked legacy).
- Depends on T8 (testing.py updated — MockBackend needs compatible create_tables).
- T10 depends on this (integration tests follow unit test patterns).

## Implementation steps (developer-facing)

### A. Update `MockBackend` in `conftest.py`

1. **Update `increment_user_exercise_score`**:
   - Remove `exercise_type: str` parameter.
   - Key becomes `(table, user_id, source_word_id)` — the exercise type is implicit in the table name.
   - New signature: `async def increment_user_exercise_score(self, table, user_id, source_word_id, delta) -> int`

2. **Update `get_user_exercise_scores`**:
   - Remove `exercise_types: list[str]` parameter.
   - New signature: `async def get_user_exercise_scores(self, table, user_id, source_word_ids) -> list[dict]`
   - Filter by `tbl == table and uid == user_id and wid in source_word_ids`.
   - Return dicts with `source_word_id` and `score` (no `exercise_type`).

3. **Update `create_tables`**:
   - Add `exercise_slugs: list[str]` parameter.
   - Can remain a no-op (mock doesn't create real tables).

4. **Add `check_event_applied` method**:
   ```python
   async def check_event_applied(self, table: str, event_id: str) -> bool:
       return event_id in self._applied_events.get(table, set())
   ```
   - Add `self._applied_events: dict[str, set[str]] = {}` to `__init__`.

5. **Add `mark_event_applied` method**:
   ```python
   async def mark_event_applied(self, table: str, event_id: str) -> None:
       self._applied_events.setdefault(table, set()).add(event_id)
   ```

### B. Update `progress_store` fixture in `conftest.py`

6. Update fixture to pass `exercise_types`:
   ```python
   store = ExerciseProgressStore(
       user_id="u1",
       source_language=Language.NL,
       target_language=Language.RU,
       exercise_types=["flashcard", "typing"],
   )
   ```

### C. Rewrite `test_exercise_progress.py`

7. **Update `_seed_word_pair` helper**: Keep as-is (returns word IDs). Store the returned `src_id` for use in `increment` calls.

8. **Update `test_increment_positive`**:
   - Change `progress_store.increment(_HUIS, "flashcard", delta=1)` → `progress_store.increment(1, "flashcard", delta=1)` (word ID 1 from seed).
   - Update score key check: key becomes `("nl_ru_flashcard", "u1", 1)` (no exercise_type in key).

9. **Update `test_increment_negative`**: Same pattern — use word ID, update key.

10. **Update `test_increment_delta_zero_raises`**: Change to `progress_store.increment(1, "flashcard", delta=0)`.

11. **Update `test_increment_delta_two_raises`**: Change to `progress_store.increment(1, "flashcard", delta=2)`.

12. **Update `test_increment_missing_word_raises`**: Remove this test. `increment` no longer does word lookup — it takes a word ID directly. There's no "missing word" error from `increment` anymore. Replace with `test_increment_unknown_exercise_type_raises` — test that an exercise_type not in the configured set raises `ValueError`.

13. **Update `test_get_scored_pairs`**:
    - Use word ID for `increment`.
    - Change `get_word_pairs_with_scores(["flashcard"])` → `get_word_pairs_with_scores()`.
    - Check `source_word_id` field on result.

14. **Update `test_missing_scores_default_zero`**: Change `get_word_pairs_with_scores(["flashcard"])` → `get_word_pairs_with_scores()`.

15. **Update `test_empty_exercise_types`**: Remove or rework. The method no longer takes `exercise_types` as a param. Instead, test that if `ExerciseProgressStore` is constructed with one exercise type, scores only include that type.

16. **Add new test: `test_constructor_raises_empty_exercise_types`**:
    ```python
    def test_constructor_raises_empty_exercise_types(monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "mock://test")
        with pytest.raises(ValueError, match="exercise_types"):
            ExerciseProgressStore(
                user_id="u1",
                source_language=Language.NL,
                target_language=Language.RU,
                exercise_types=[],
            )
    ```

17. **Add new test: `test_increment_unknown_exercise_type_raises`**:
    ```python
    async def test_increment_unknown_exercise_type_raises(progress_store, mock_backend):
        await _seed_word_pair(mock_backend)
        with pytest.raises(ValueError, match="not in configured set"):
            await progress_store.increment(1, "unknown_type", delta=1)
    ```

18. **Add new test: `test_export_remote_snapshot`**:
    ```python
    async def test_export_remote_snapshot(progress_store, mock_backend):
        await _seed_word_pair(mock_backend)
        snapshot = await progress_store.export_remote_snapshot()
        assert len(snapshot) == 1
        assert snapshot[0].source_word_id == 1
    ```

19. **Add new test: `test_apply_score_delta_idempotent`**:
    ```python
    async def test_apply_score_delta_idempotent(progress_store, mock_backend):
        await _seed_word_pair(mock_backend)
        await progress_store.apply_score_delta("evt1", 1, "flashcard", 1)
        await progress_store.apply_score_delta("evt1", 1, "flashcard", 1)  # duplicate
        scored = await progress_store.get_word_pairs_with_scores()
        assert scored[0].scores["flashcard"] == 1  # applied only once
    ```

20. **Add new test: `test_apply_score_delta_different_events`**:
    ```python
    async def test_apply_score_delta_different_events(progress_store, mock_backend):
        await _seed_word_pair(mock_backend)
        await progress_store.apply_score_delta("evt1", 1, "flashcard", 1)
        await progress_store.apply_score_delta("evt2", 1, "flashcard", 1)
        scored = await progress_store.get_word_pairs_with_scores()
        assert scored[0].scores["flashcard"] == 2
    ```

### D. Minor updates to `test_service.py`

21. **No changes needed for `DatabaseService` tests** — they don't use `ExerciseProgressStore`. The `_DOM` word test now passes (T1 fixed it). Verify all tests pass as-is.

### E. Line count and quality checks

22. Run linters:
    ```
    uv run ruff format tests/unit/database/
    uv run ruff check tests/unit/database/
    ```

23. Run all unit tests:
    ```
    uv run pytest tests/unit/database/ -x -v
    ```

24. Check line counts: `conftest.py` (currently 169, adding ~15 lines → ~184). `test_exercise_progress.py` (currently 108, net change ~+15 → ~123). Both under 200.

## Production safety constraints (mandatory)

- **Database operations**: Unit tests use `MockBackend` — no real DB connection.
- **Resource isolation**: N/A.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Extends existing MockBackend and test patterns.
- **No regressions**: All existing tests are updated to match new APIs.

## Error handling + correctness rules (mandatory)

- Tests verify that `ValueError` is raised for invalid inputs (empty exercise_types, unknown exercise_type, invalid delta).
- Tests verify idempotency behavior (same event_id → no double-apply).

## Zero legacy tolerance rule (mandatory)

- Old test code using `Word` objects in `increment` calls is fully replaced.
- Old test code passing `exercise_types` to `get_word_pairs_with_scores` is fully removed.
- `test_increment_missing_word_raises` is replaced by `test_increment_unknown_exercise_type_raises`.

## Acceptance criteria (testable)

1. `uv run pytest tests/unit/database/ -x -v` — all tests pass (zero failures).
2. `MockBackend` implements all methods of updated `AbstractBackend`.
3. `progress_store` fixture passes `exercise_types=["flashcard", "typing"]`.
4. All `ExerciseProgressStore` tests use `source_word_id: int` for `increment`.
5. All `get_word_pairs_with_scores` calls have no arguments.
6. New tests exist for: empty exercise_types constructor, unknown exercise_type in increment, export_remote_snapshot, apply_score_delta idempotency.
7. All test files ≤ 200 lines.
8. `uv run ruff check tests/unit/database/` — no errors.

## Verification / quality gates

- [x] Unit tests added/updated
- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] Negative-path tests exist (empty exercise_types, unknown exercise_type, invalid delta)

## Edge cases

- MockBackend `increment_user_exercise_score` with different table names (per exercise type): scores stored under separate keys.
- `apply_score_delta` idempotency in MockBackend: `_applied_events` dict tracks event IDs correctly.

## Notes / risks

- **Risk**: `conftest.py` line count (currently 169). Adding ~15 lines for new MockBackend methods may push to ~184. Under 200.
- **Risk**: Some tests in `test_service.py` may need updates if `ScoredWordPair` construction changed (added `source_word_id`). However, `test_service.py` doesn't directly construct `ScoredWordPair` — it tests `DatabaseService`, not `ExerciseProgressStore`. Should be fine.
