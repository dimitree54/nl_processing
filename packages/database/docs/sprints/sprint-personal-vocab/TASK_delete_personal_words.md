---
Task ID: `T5`
Title: `Implement delete_word() and delete_words() APIs on DatabaseService (FR-9)`
Sprint: `2026-03-12_personal-vocab`
Module: `database`
Depends on: `T1`
Parallelizable: `yes, with T2, T3, T4`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Expose `delete_word(source_word_id)` and `delete_words(source_word_ids)` on `DatabaseService` that remove only the requesting user's membership rows (`user_words`) and exercise-score rows. Shared corpus rows (`words_*`) and translation links (`translations_*`) remain intact. Requesting deletion of a source_word_id outside the user's vocabulary raises an explicit domain error (FM-5).

## Context (contract mapping)

- Requirements: `docs/module-spec.md` — FR-9 (delete APIs for one/many source-word IDs), BR-7 (deletes remove only per-user state), FM-5 (delete for non-existent ID raises domain error), DEC-6 (delete scoped to membership and scores)
- Module spec: `docs/module-spec.md` — IF-1 (DatabaseService.delete_word(), delete_words()), Processing Flow step 5, AC-6

## Preconditions

- T1 complete: backend query infrastructure is in place (though delete does not depend on `added_at` specifically, T1 ensures the backend layer is stable).
- `user_words` table has the `(user_id, word_id, language)` UNIQUE constraint for deletion targeting.
- Exercise score tables have `(user_id, source_word_id)` UNIQUE constraint.

## Non-goals

- Deleting corpus words or translation links (BR-7 explicitly forbids this).
- Cascade deletes to other users' data.
- Undo/soft-delete functionality.
- Batch delete optimization (simple loop over single-word delete is acceptable for V1).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `src/nl_processing/database/backend/abstract.py` — add abstract delete methods
- `src/nl_processing/database/backend/neon.py` — implement delete methods (or extract to new file)
- `src/nl_processing/database/backend/_queries.py` — add delete SQL queries (or extract to new file if approaching 200 lines)
- `src/nl_processing/database/backend/_neon_delete.py` — new file for delete backend operations (following `_neon_exercise.py` pattern)
- `src/nl_processing/database/backend/_queries_delete.py` — new file for delete SQL queries if `_queries.py` would exceed 200 lines
- `src/nl_processing/database/service.py` — add `delete_word()` and `delete_words()` methods
- `src/nl_processing/database/exceptions.py` — add `WordNotFoundError` or similar domain error for FM-5
- `tests/unit/database/conftest.py` — add delete mock methods to `MockBackend`
- `tests/unit/database/` — add unit tests for delete
- `tests/integration/database/` — add integration tests for delete
- `tests/e2e/database/` — add e2e tests for delete

**FORBIDDEN — this task must NEVER touch:**
- `packages/core/` or any core package file
- Any other module's code or tests

**Test scope:**
- Tests go in: `tests/unit/database/`, `tests/integration/database/`, `tests/e2e/database/`
- Test command: `make check`

## Touched surface (expected files / modules)

- `src/nl_processing/database/exceptions.py` — new `WordNotFoundError`
- `src/nl_processing/database/backend/abstract.py` — new abstract methods for delete
- `src/nl_processing/database/backend/_queries_delete.py` — new file with delete SQL queries
- `src/nl_processing/database/backend/_neon_delete.py` — new file with delete backend operations
- `src/nl_processing/database/backend/neon.py` — implement abstract delete methods (delegate to `_neon_delete.py`)
- `src/nl_processing/database/service.py` — `delete_word()` and `delete_words()` methods
- `tests/unit/database/conftest.py` — `MockBackend` delete methods
- `tests/unit/database/test_delete.py` — new unit test file
- `tests/integration/database/test_delete.py` — new integration test file
- `tests/e2e/database/test_delete.py` — new e2e test file

## Dependencies and sequencing notes

- Depends on T1 only for backend layer stability — no direct dependency on `added_at`.
- Fully parallel with T2, T3, T4. File contention is minimal:
  - T5 modifies `abstract.py`, `neon.py`, `_queries.py` (or new files), `service.py`, `conftest.py`.
  - T3 also modifies `service.py` — potential contention. If running in parallel, coordinate on `service.py`.
  - If serialized after T3, `service.py` will already be decomposed, which helps.

## Third-party / library research (mandatory for any external dependency)

No new external dependencies. Uses:
- `asyncpg` — existing; DELETE SQL via `conn.execute()` (same pattern as INSERT/UPDATE).
- Standard PostgreSQL `DELETE FROM ... WHERE ...` syntax.

## Implementation steps (developer-facing)

1. **Add `WordNotFoundError` to `exceptions.py`**:
   ```python
   class WordNotFoundError(DatabaseError):
       """Raised when a delete targets a source_word_id not in the user's vocabulary (FM-5)."""
   ```
   - `exceptions.py` goes from 6 to ~10 lines — well under 200.

2. **Add delete SQL queries**:
   - **Decision**: `_queries.py` is at 187 lines. Adding 3-4 delete query functions (~30 lines) would push it to ~217. **Must create a new file**.
   - Create `src/nl_processing/database/backend/_queries_delete.py`:
     ```python
     def delete_user_word_query(language: str) -> str:
         """Delete a user's membership row for a specific source word."""
         return f"""
             DELETE FROM user_words
             WHERE user_id = $1 AND word_id = $2 AND language = $3
         """

     def check_user_word_exists_query(language: str) -> str:
         """Check if a source_word_id belongs to the user's vocabulary."""
         return f"""
             SELECT 1 FROM user_words uw
             JOIN words_{language} sw ON uw.word_id = sw.id
             WHERE uw.user_id = $1 AND sw.id = $2 AND uw.language = $3
         """

     def delete_user_exercise_scores_query(table: str) -> str:
         """Delete a user's exercise scores for a specific source word."""
         return f"""
             DELETE FROM user_word_exercise_scores_{table}
             WHERE user_id = $1 AND source_word_id = $2
         """
     ```

3. **Add abstract delete methods to `abstract.py`**:
   - Add two abstract methods:
     ```python
     @abstractmethod
     async def check_user_word_exists(
         self, user_id: str, source_word_id: int, language: str,
     ) -> bool:
         """Check if a source word is in the user's vocabulary."""

     @abstractmethod
     async def delete_user_word(
         self, user_id: str, source_word_id: int, language: str,
     ) -> None:
         """Delete the user's membership row for a source word."""

     @abstractmethod
     async def delete_user_exercise_score(
         self, table: str, user_id: str, source_word_id: int,
     ) -> None:
         """Delete the user's exercise score for a source word in one exercise table."""
     ```
   - `abstract.py` goes from 142 to ~165 lines — safe under 200.

4. **Create `_neon_delete.py`** for the Neon implementation:
   - Follow the `_neon_exercise.py` pattern — standalone async functions that take a connection.
   ```python
   async def check_word_exists(conn, user_id, source_word_id, language) -> bool: ...
   async def delete_word_membership(conn, user_id, source_word_id, language) -> None: ...
   async def delete_exercise_score(conn, table, user_id, source_word_id) -> None: ...
   ```
   - Wrap all in `try/except asyncpg.PostgresError → raise DatabaseError`.

5. **Implement abstract methods on `NeonBackend` in `neon.py`**:
   - Delegate to `_neon_delete.py` functions (same pattern as exercise methods delegate to `_neon_exercise.py`).
   - `neon.py` is at 182 lines. Adding 3 thin delegate methods (~12 lines) → ~194. **Still under 200** but monitor.

6. **Add `delete_word()` and `delete_words()` to `DatabaseService` in `service.py`**:
   ```python
   async def delete_word(self, source_word_id: int, exercise_types: list[str] | None = None) -> None:
       """Delete one personal-vocabulary entry (FR-9, BR-7, FM-5)."""
       exists = await self._backend.check_user_word_exists(
           self._user_id, source_word_id, self._source_language.value,
       )
       if not exists:
           raise WordNotFoundError(
               f"Source word ID {source_word_id} not in user's vocabulary"
           )
       # Delete exercise scores first (no FK, but clean ordering)
       if exercise_types:
           src = self._source_language.value
           tgt = self._target_language.value
           for et in exercise_types:
               table = f"{src}_{tgt}_{et}"
               await self._backend.delete_user_exercise_score(table, self._user_id, source_word_id)
       # Delete user_words membership
       await self._backend.delete_user_word(
           self._user_id, source_word_id, self._source_language.value,
       )

   async def delete_words(self, source_word_ids: list[int], exercise_types: list[str] | None = None) -> None:
       """Delete many personal-vocabulary entries (FR-9)."""
       for source_word_id in source_word_ids:
           await self.delete_word(source_word_id, exercise_types=exercise_types)
   ```
   - **Line count**: `service.py` is at 180 (or decomposed by T3). Adding ~20 lines for delete methods. If T3 decomposed `service.py`, there should be room. If not, these methods push it to ~200. The developer must ensure the file stays under 200 — either by relying on T3's decomposition or by extracting delete logic into a separate module.

7. **Update `MockBackend` in `conftest.py`**:
   - Add `check_user_word_exists()`, `delete_user_word()`, `delete_user_exercise_score()` implementations.
   - `check_user_word_exists`: iterate `self._user_words` to find matching `(user_id, word_id, language)` where `word_id` maps to the given `source_word_id`.
   - `delete_user_word`: remove the matching tuple from `self._user_words`.
   - `delete_user_exercise_score`: remove matching keys from `self._scores`.
   - **Line count**: `conftest.py` is at 198 (or already decomposed). Adding ~20 lines for 3 methods → exceeds 200. **Must extract `MockBackend` into `tests/unit/database/mock_backend.py`** and import in `conftest.py`.

8. **Write unit tests in `tests/unit/database/test_delete.py`** (new file):
   - `test_delete_word_removes_membership`: Add word, delete it, verify `get_user_words` returns empty.
   - `test_delete_word_removes_exercise_scores`: Add word + score, delete with exercise_types, verify score gone.
   - `test_delete_word_preserves_corpus`: After delete, word still exists in `words_nl` table.
   - `test_delete_word_preserves_translation_link`: After delete, translation link still exists.
   - `test_delete_word_not_found_raises`: Delete non-existent ID → `WordNotFoundError`.
   - `test_delete_words_bulk`: Delete multiple words, verify all removed.
   - `test_delete_words_partial_failure_raises`: One ID exists, one doesn't → raises on the non-existent one (fail-fast).
   - `test_delete_word_other_users_unaffected`: Two users have the same word; delete for user A doesn't affect user B.

9. **Write integration tests in `tests/integration/database/test_delete.py`** (new file):
   - Insert words, translations, user associations, and scores into real Neon DB.
   - Delete via backend methods, verify membership and scores gone, corpus and links intact.

10. **Write e2e test in `tests/e2e/database/test_delete.py`** (new file):
    - Full flow: add words via service with translations, delete one word, verify `get_words()` no longer includes it.
    - Delete non-existent ID, verify `WordNotFoundError`.

11. **Run `make check`** and verify all tests pass, all files under 200 lines.

## Production safety constraints (mandatory)

- **Database operations**: DELETE operations target only test DB via Doppler-managed `DATABASE_URL`. UUID-based user isolation ensures no cross-test interference.
- **Resource isolation**: No port or file conflicts. Advisory locks for e2e tests.
- **Migration preparation**: N/A — no schema changes. DELETE operations use existing table structure.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follows existing backend patterns (`_neon_exercise.py` extraction, `_queries.py` query functions).
- **Correct libraries only**: `asyncpg`, `pydantic` — already used.
- **Correct file locations**: New files follow existing naming pattern (`_neon_delete.py`, `_queries_delete.py`).
- **No regressions**: Delete methods are new; no existing methods modified.
- **BR-7 critical**: Tests MUST verify that `words_*` rows and `translations_*` rows are NOT deleted.

## Error handling + correctness rules (mandatory)

- **FM-5**: Delete for a `source_word_id` not in the user's vocabulary MUST raise `WordNotFoundError` — no silent success.
- `delete_words()` iterates and calls `delete_word()` for each ID. If any ID is not found, the error is raised immediately (fail-fast). Previously deleted IDs in the same batch are already committed (no transaction rollback across the batch). This is acceptable per spec — the caller can retry with corrected IDs.
- No empty `catch` blocks. Backend errors propagate as `DatabaseError`.
- No fallback behavior (e.g., no "skip missing IDs" mode).

## Zero legacy tolerance rule (mandatory)

- No dead code introduced. New files and methods only.
- If `MockBackend` is extracted to a new file, update all imports in test files.

## Acceptance criteria (testable)

1. `WordNotFoundError` exists in `database.exceptions`, subclass of `DatabaseError`.
2. `DatabaseService.delete_word(source_word_id, exercise_types?)` removes user's `user_words` row for that source_word_id.
3. `delete_word()` also removes user's exercise-score rows for that source_word_id across provided exercise types.
4. `delete_word()` does NOT delete the canonical word row in `words_*` (BR-7).
5. `delete_word()` does NOT delete the translation link in `translations_*` (BR-7).
6. `delete_word()` raises `WordNotFoundError` when source_word_id is not in user's vocabulary (FM-5).
7. `DatabaseService.delete_words(source_word_ids, exercise_types?)` deletes multiple entries.
8. `delete_words()` raises `WordNotFoundError` on the first non-existent ID (fail-fast).
9. Other users' data is unaffected by a delete.
10. New abstract methods exist on `AbstractBackend`: `check_user_word_exists`, `delete_user_word`, `delete_user_exercise_score`.
11. `NeonBackend` implements all new abstract methods.
12. Unit tests cover: happy path, not-found error, corpus preservation, translation preservation, multi-user isolation, bulk delete.
13. Integration tests verify real DB delete behavior.
14. E2e test confirms full flow.
15. All source files ≤ 200 lines.
16. `make check` is green.

## Verification / quality gates

- [ ] Unit tests added for all delete scenarios (happy, error, preservation, isolation)
- [ ] Integration tests added for backend delete methods
- [ ] E2e test added for full delete flow
- [ ] `make check` green
- [ ] No new warnings
- [ ] All source files ≤ 200 lines
- [ ] All test files ≤ 200 lines
- [ ] Negative-path test: `WordNotFoundError` for non-existent source_word_id
- [ ] Preservation test: corpus and translation rows intact after delete

## Edge cases

- Delete the same word twice → first succeeds, second raises `WordNotFoundError`.
- Delete word that exists in corpus but not in user's vocabulary → `WordNotFoundError`.
- Delete word with no exercise scores → membership deleted, no score deletion errors.
- Delete word shared between two users → only the requesting user's membership and scores removed.
- `delete_words([])` → no-op (empty list, nothing to delete, no error).
- `delete_words([valid_id, invalid_id])` → `valid_id` is deleted, then `WordNotFoundError` for `invalid_id` (partial success).

## Notes / risks

- **Risk**: `neon.py` (182 lines) adding 3 delegate methods → ~194 lines. Close to limit.
  - **Mitigation**: Delegate methods are thin (3 lines each). If any other task also adds to `neon.py`, further extraction may be needed.
- **Risk**: `conftest.py` (198 lines) adding mock methods → exceeds 200.
  - **Mitigation**: Extract `MockBackend` into `tests/unit/database/mock_backend.py`. This is a clean refactoring that T3 might also need.
- **Risk**: `abstract.py` (142 lines) adding 3 abstract methods → ~165 lines. Safe.
- **Risk**: Partial success in `delete_words()` — some IDs deleted before error.
  - **Mitigation**: Document this behavior. The spec doesn't require transactional batch delete. Fail-fast is the correct approach per project principles.
- **Risk**: `service.py` line count depends on T3's decomposition.
  - **Mitigation**: If T3 ran first and decomposed `service.py`, there's room. If T5 runs before T3, the developer must also decompose `service.py`.
