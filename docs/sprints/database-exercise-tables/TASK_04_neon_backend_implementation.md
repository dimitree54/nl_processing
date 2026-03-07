---
Task ID: `T4`
Title: `Update NeonBackend to implement new per-exercise-type abstract methods`
Sprint: `2026-03-07_database-exercise-tables`
Module: `database`
Depends on: `T3`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Update `NeonBackend` to implement the changed `AbstractBackend` signatures: per-exercise-type table creation, updated score increment/get methods (no `exercise_type` param), and new event-tracking methods (`check_event_applied`, `mark_event_applied`). After this task, the backend layer is fully updated for per-exercise-type tables.

## Context (contract mapping)

- Requirements: Sprint request items 1, 3
- Current: `neon.py` (184 lines) — close to the 200-line limit.
- `create_tables` currently calls `create_exercise_scores_table(src, tgt)` per pair.
- `increment_user_exercise_score` takes `exercise_type` param.
- `get_user_exercise_scores` takes `exercise_types` param.

## Preconditions

- T2 completed (query templates updated).
- T3 completed (abstract method signatures updated).

## Non-goals

- Updating `ExerciseProgressStore` (T5).
- Updating tests (T9/T10).
- Splitting `neon.py` if already under 200 lines.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/database/backend/neon.py` — concrete backend implementation

**FORBIDDEN — this task must NEVER touch:**
- `nl_processing/database/backend/_queries.py` (done in T2)
- `nl_processing/database/backend/abstract.py` (done in T3)
- Any test files
- Any other module

**Test scope:**
- No tests run for this task in isolation (backend is tested via integration tests in T10).
- Linter check: `uv run ruff check nl_processing/database/backend/neon.py`

## Touched surface (expected files / modules)

- `nl_processing/database/backend/neon.py`

## Dependencies and sequencing notes

- Depends on T3 (abstract signatures must be finalized).
- T5 depends on this (ExerciseProgressStore calls backend methods).
- T8 depends on this (testing utilities reference backend's `create_tables`).

## Implementation steps (developer-facing)

1. **Update imports** from `_queries.py`:
   - Add imports for: `create_applied_events_table`, `check_event_applied_query`, `mark_event_applied_query`
   - Existing imports for score functions remain (they changed signatures but not names).

2. **Update `create_tables` method**:
   - Add `exercise_slugs: list[str]` parameter to match new ABC signature.
   - Replace the per-pair `create_exercise_scores_table(src, tgt)` loop with a nested loop:
     ```python
     for src, tgt in pairs:
         for slug in exercise_slugs:
             await conn.execute(create_exercise_scores_table(src, tgt, slug))
     ```
   - Add `applied_events` table creation:
     ```python
     for src, tgt in pairs:
         await conn.execute(create_applied_events_table(src, tgt))
     ```

3. **Update `increment_user_exercise_score`**:
   - Remove `exercise_type: str` parameter.
   - Update `fetchrow` call to pass only 3 args: `user_id`, `source_word_id`, `delta`.
   - The `table` parameter now carries the exercise slug (e.g., `nl_ru_flashcard`).

4. **Update `get_user_exercise_scores`**:
   - Remove `exercise_types: list[str]` parameter.
   - Guard clause becomes `if not source_word_ids: return []`.
   - Update `fetch` call to pass only 2 args: `user_id`, `source_word_ids`.

5. **Add `check_event_applied` method**:
   ```python
   async def check_event_applied(self, table: str, event_id: str) -> bool:
       conn = await self._connect()
       try:
           row = await conn.fetchrow(check_event_applied_query(table), event_id)
       except asyncpg.PostgresError as exc:
           raise DatabaseError(str(exc)) from exc
       return row is not None
   ```

6. **Add `mark_event_applied` method**:
   ```python
   async def mark_event_applied(self, table: str, event_id: str) -> None:
       conn = await self._connect()
       try:
           await conn.execute(mark_event_applied_query(table), event_id)
       except asyncpg.PostgresError as exc:
           raise DatabaseError(str(exc)) from exc
   ```

7. **Line count check**: Current is 184. Removed params from 2 methods (saves ~2 lines). Added 2 new methods (~16 lines). Updated `create_tables` loop (~3 lines net). Estimate ~200–202 lines. **If over 200**: extract the `_infer_target_language` helper and event-tracking methods into a small helper, OR compress method bodies slightly (combine try/except lines where safe).

8. **Linter check**:
   ```
   uv run ruff format nl_processing/database/backend/neon.py
   uv run ruff check nl_processing/database/backend/neon.py
   ```

## Production safety constraints (mandatory)

- **Database operations**: No DB connections during this task (implementation only, no tests run).
- **Resource isolation**: N/A for code changes.
- **Migration preparation**: N/A (DDL execution happens at table creation time; migration is separate).

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follows existing NeonBackend patterns (connect, try/except, wrap in DatabaseError).
- **Correct file locations**: Same file.
- **No regressions**: Method signatures changed — old callers must be updated in T5. Between T4 and T5, `ExerciseProgressStore` will call methods with wrong signatures. This is expected.

## Error handling + correctness rules (mandatory)

- All new methods follow the existing pattern: `try/except asyncpg.PostgresError as exc: raise DatabaseError(str(exc)) from exc`.
- No errors silenced.

## Zero legacy tolerance rule (mandatory)

- Old `increment_user_exercise_score` with `exercise_type` param is replaced.
- Old `get_user_exercise_scores` with `exercise_types` param is replaced.
- Old `create_tables` without `exercise_slugs` is replaced.

## Acceptance criteria (testable)

1. `NeonBackend` satisfies `AbstractBackend` ABC (no missing abstract methods).
2. `create_tables` accepts `exercise_slugs` and creates per-exercise-type tables.
3. `increment_user_exercise_score` takes `table, user_id, source_word_id, delta` (no `exercise_type`).
4. `get_user_exercise_scores` takes `table, user_id, source_word_ids` (no `exercise_types`).
5. `check_event_applied` and `mark_event_applied` methods exist.
6. `uv run ruff check nl_processing/database/backend/neon.py` — no errors.
7. File is ≤ 200 lines. If it exceeds, developer must split (document the split in commit message).

## Verification / quality gates

- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] File ≤ 200 lines (HARD constraint — split if needed)
- [ ] All abstract methods implemented

## Edge cases

- Connection failure during `check_event_applied` or `mark_event_applied`: handled by existing `asyncpg.PostgresError` → `DatabaseError` pattern.

## Notes / risks

- **Risk**: 200-line limit is tight. If the file exceeds 200 lines, the developer must extract the event-tracking methods (or `_infer_target_language`) to a separate private module. Possible split: `nl_processing/database/backend/_event_tracking.py` with `check_event_applied` and `mark_event_applied` as standalone async functions that take a connection.
