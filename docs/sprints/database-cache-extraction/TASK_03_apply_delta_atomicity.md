---
Task ID: `T3`
Title: `Make apply_score_delta atomic (fix TOCTOU race)`
Sprint: `2026-03-07_database-cache-extraction`
Module: `database`
Depends on: `T2`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Make the `apply_score_delta` operation atomic by executing the check-increment-mark sequence inside a single database transaction. Currently, `check_event_applied`, `increment_user_exercise_score`, and `mark_event_applied` are three separate queries with no transaction wrapping, creating a TOCTOU race condition where a crash between queries could double-apply a delta or lose the event marker.

## Context (contract mapping)

- Requirements: `nl_processing/database/docs/prd_database.md` FR39-40 -- "event_id is treated as an idempotency key" and "Repeating the same event_id must not double-apply the remote score delta."
- Architecture: `nl_processing/database/docs/architecture_database.md` -- "Decision: Idempotent Score Replay."
- Sprint request: Discrepancy 7 -- "`apply_score_delta` not atomic (TOCTOU race)."

## Preconditions

- T2 completed (delta validation added to `apply_score_delta`).
- `make check` is green before starting.

## Non-goals

- Changing `increment()` -- it does not use event deduplication and doesn't need transaction wrapping.
- Adding a generic transaction API to `AbstractBackend` -- we add only the specific atomic method needed.
- Changing the data model or schema.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `nl_processing/database/backend/abstract.py` -- add `apply_score_delta_atomic` abstract method
- `nl_processing/database/backend/neon.py` -- implement `apply_score_delta_atomic`
- `nl_processing/database/backend/_neon_exercise.py` -- add atomic helper function
- `nl_processing/database/exercise_progress.py` -- use new atomic method instead of three separate calls
- `tests/unit/database/conftest.py` -- add `apply_score_delta_atomic` to MockBackend
- `tests/unit/database/test_exercise_progress.py` -- verify atomicity behavior
- `vulture_whitelist.py` -- add whitelist entries for new abstract method if needed

**FORBIDDEN -- this task must NEVER touch:**
- Any other module's code or tests
- `nl_processing/database/service.py`
- Integration or e2e tests (they already test `apply_score_delta` idempotency; the new atomic method is transparent to them)

**Test scope:**
- Verification command: `make check`
- Unit tests in: `tests/unit/database/test_exercise_progress.py`

## Touched surface (expected files / modules)

- `nl_processing/database/backend/abstract.py` (~15 lines added) -- new abstract method
- `nl_processing/database/backend/neon.py` (~8 lines added) -- delegate to helper
- `nl_processing/database/backend/_neon_exercise.py` (~25 lines added) -- atomic helper using asyncpg transaction
- `nl_processing/database/exercise_progress.py` (~5 lines changed) -- replace 3 calls with 1
- `tests/unit/database/conftest.py` (~15 lines added) -- MockBackend method
- `tests/unit/database/test_exercise_progress.py` (~10 lines added) -- verify behavior
- `vulture_whitelist.py` (~3 lines added) -- whitelist new abstract method + params

## Dependencies and sequencing notes

- Depends on T2 because T2 adds delta validation to `apply_score_delta`. The method body changes in both tasks.
- Cannot run in parallel with T2 (same method modified).

## Third-party / library research (mandatory for any external dependency)

- **Library/API**: `asyncpg` (already in use, version managed by `pyproject.toml`)
- **Official documentation**: https://magicstack.github.io/asyncpg/current/api/index.html#asyncpg.connection.Connection.transaction
- **API reference**: `Connection.transaction()` returns an async context manager that wraps statements in a PostgreSQL transaction. On `__aexit__` with an exception, it rolls back; on clean exit, it commits.
- **Usage pattern (verified)**:
  ```python
  async with conn.transaction():
      row = await conn.fetchrow(...)
      await conn.execute(...)
  ```
- **Known gotchas**: asyncpg does not support nested transactions by default. Since the current code uses a single connection with no existing transaction context, wrapping these three operations in a single `async with conn.transaction()` is safe.

## Implementation steps (developer-facing)

1. **Add abstract method to `nl_processing/database/backend/abstract.py`:**
   ```python
   @abstractmethod
   async def apply_score_delta_atomic(
       self,
       score_table: str,
       events_table: str,
       user_id: str,
       event_id: str,
       source_word_id: int,
       delta: int,
   ) -> bool:
       """Atomically check-apply-mark a score delta in one transaction.

       Returns True if the delta was applied, False if event_id was already applied.
       The entire operation (check + increment + mark) runs in a single transaction.
       """
   ```

2. **Add atomic helper to `nl_processing/database/backend/_neon_exercise.py`:**
   ```python
   async def apply_score_delta_atomic(
       conn: asyncpg.Connection,
       score_table: str,
       events_table: str,
       user_id: str,
       event_id: str,
       source_word_id: int,
       delta: int,
   ) -> bool:
       """Atomically check-apply-mark a score delta in one transaction.

       Returns True if applied, False if already applied.
       """
       try:
           async with conn.transaction():
               already = await conn.fetchrow(
                   check_event_applied_query(events_table), event_id
               )
               if already is not None:
                   return False
               await conn.fetchrow(
                   increment_score_query(score_table),
                   user_id, source_word_id, delta,
               )
               await conn.execute(
                   mark_event_applied_query(events_table), event_id
               )
               return True
       except asyncpg.PostgresError as exc:
           raise DatabaseError(str(exc)) from exc
   ```

3. **Implement in `nl_processing/database/backend/neon.py`:**
   Add the import for the new helper in the existing import block from `_neon_exercise`, then add the method:
   ```python
   async def apply_score_delta_atomic(
       self,
       score_table: str,
       events_table: str,
       user_id: str,
       event_id: str,
       source_word_id: int,
       delta: int,
   ) -> bool:
       conn = await self._connect()
       return await apply_score_delta_atomic_fn(
           conn, score_table, events_table, user_id, event_id, source_word_id, delta
       )
   ```
   Note: import the helper under a distinct name (e.g., `apply_score_delta_atomic as apply_score_delta_atomic_fn` or rename the helper to `atomic_apply_score_delta`) to avoid name collision with the method. The simplest approach: name the helper function in `_neon_exercise.py` as `atomic_apply_delta` and import it.

4. **Update `nl_processing/database/exercise_progress.py`** method `apply_score_delta`:
   Replace the three separate calls:
   ```python
   # OLD (remove):
   already_applied = await self._backend.check_event_applied(...)
   if already_applied:
       return
   table = self._score_tables[exercise_type]
   await self._backend.increment_user_exercise_score(...)
   await self._backend.mark_event_applied(...)
   ```
   With a single atomic call:
   ```python
   # NEW:
   table = self._score_tables[exercise_type]
   await self._backend.apply_score_delta_atomic(
       score_table=table,
       events_table=self._applied_events_table,
       user_id=self._user_id,
       event_id=event_id,
       source_word_id=source_word_id,
       delta=delta,
   )
   ```

5. **Update `tests/unit/database/conftest.py`** -- add `apply_score_delta_atomic` to `MockBackend`:
   ```python
   async def apply_score_delta_atomic(
       self,
       score_table: str,
       events_table: str,
       user_id: str,
       event_id: str,
       source_word_id: int,
       delta: int,
   ) -> bool:
       if (events_table, event_id) in self._applied_events:
           return False
       key = (score_table, user_id, source_word_id)
       self._scores[key] = self._scores.get(key, 0) + delta
       self._applied_events.add((events_table, event_id))
       return True
   ```

6. **Update `vulture_whitelist.py`:**
   - Add `AbstractBackend.apply_score_delta_atomic  # type: ignore[misc]` after existing abstract method entries.
   - Add `NeonBackend.apply_score_delta_atomic  # type: ignore[misc]` after existing NeonBackend entries.
   - Add parameter names `score_table` and `events_table` to the bare-name whitelist section if vulture flags them.

7. **Verify existing test `test_apply_score_delta_applies_once` still passes** -- it tests idempotency which should work identically through the new atomic path.

8. **Run `make check`** and confirm 100% green.

## Production safety constraints (mandatory)

- **Database operations**: The atomic method wraps existing queries in a transaction. No new tables, columns, or schema changes. The transaction is extremely short-lived (3 statements).
- **Resource isolation**: Uses the same connection and database as existing code. No new resources.
- **Migration preparation**: N/A -- no schema changes.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Reuses existing query functions (`check_event_applied_query`, `increment_score_query`, `mark_event_applied_query`). No new SQL.
- **Correct libraries only**: `asyncpg` transaction API, already in use.
- **Correct file locations**: All files are existing module files.
- **No regressions**: The existing `test_apply_score_delta_applies_once` unit test and e2e tests in `test_exercise_progress.py` validate idempotency. Both must continue to pass.

## Error handling + correctness rules (mandatory)

- `asyncpg.PostgresError` is caught and re-raised as `DatabaseError`, matching existing patterns.
- If any step inside the transaction fails, the entire transaction rolls back -- no partial state.
- No empty catch blocks. No silenced errors.

## Zero legacy tolerance rule (mandatory)

- The old three-separate-calls pattern in `apply_score_delta` is fully replaced.
- The individual `check_event_applied` and `mark_event_applied` methods on `AbstractBackend` remain because they may be used elsewhere or by future code. They are not dead code -- they are part of the public backend contract.

## Acceptance criteria (testable)

1. `apply_score_delta` calls `self._backend.apply_score_delta_atomic(...)` instead of three separate backend calls.
2. `AbstractBackend` has an `apply_score_delta_atomic` abstract method.
3. `NeonBackend.apply_score_delta_atomic` wraps the three operations in `async with conn.transaction()`.
4. Existing `test_apply_score_delta_applies_once` passes unchanged.
5. `make check` is 100% green.

## Verification / quality gates

- [ ] `AbstractBackend.apply_score_delta_atomic` exists as abstract method
- [ ] `NeonBackend.apply_score_delta_atomic` implemented with transaction wrapping
- [ ] `_neon_exercise.py` helper function uses `conn.transaction()`
- [ ] `ExerciseProgressStore.apply_score_delta` uses single atomic call
- [ ] `MockBackend.apply_score_delta_atomic` added to conftest
- [ ] `vulture_whitelist.py` updated for new methods
- [ ] Existing unit test passes
- [ ] Existing e2e idempotency test passes
- [ ] `make check` passes
- [ ] No new warnings introduced
- [ ] All modified files remain under 200 lines

## Edge cases

- **Concurrent calls with same `event_id`**: PostgreSQL transaction isolation ensures only one succeeds at incrementing + marking. The other sees the event as already applied.
- **Connection failure mid-transaction**: asyncpg rolls back automatically. No partial state.
- **MockBackend is not truly atomic**: acceptable for unit tests since they are single-threaded. The mock simulates the correct behavior (check-then-set) which is sufficient.

## Notes / risks

- **Risk**: `neon.py` is currently 190 lines. Adding ~10 lines for the new method brings it close to 200.
  - **Mitigation**: The method body is very short (3 lines: connect, delegate, return). If tight, the `_infer_target_language` helper at the bottom could be moved to a shared utility, but it's likely fine.
- **Risk**: `_neon_exercise.py` gains ~25 lines, going from 92 to ~117. Well within the 200-line limit.
- **Risk**: `abstract.py` gains ~15 lines, going from 117 to ~132. Well within limits.
