---
Task ID: `T4`
Title: `Add FR21 missing-translation warning logging`
Sprint: `2026-03-07_database-cache-extraction`
Module: `database`
Depends on: `--`
Parallelizable: `yes, with T1, T2`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Implement FR21: "Missing translations excluded from reads are logged as warnings." When `get_words()` returns translated word pairs, untranslated words are silently excluded by the INNER JOIN in the backend query. The user has no visibility into this. After this task, a warning is logged when the number of returned pairs is fewer than the user's total word count for the requested filters.

## Context (contract mapping)

- Requirements: `nl_processing/database/docs/prd_database.md` FR21 -- "Missing translations excluded from reads are logged as warnings."
- Requirements: `nl_processing/database/docs/prd_database.md` FR12 -- "Words without completed translations are excluded from `get_words()` results."
- Architecture: `nl_processing/database/docs/architecture_database.md` -- "Decision: Structured Logging with Sync Visibility."
- Sprint request: Discrepancy 5 -- "FR21 -- Missing translation warning logging."

## Preconditions

- `make check` is green before starting.

## Non-goals

- Changing the behavior of `get_words()` (it still excludes untranslated words).
- Adding a separate count query to the backend (use a lightweight approach).
- Logging every excluded word individually (just a summary warning).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `nl_processing/database/service.py` -- add warning log in `get_words()`
- `tests/unit/database/test_service.py` -- add unit test for the warning
- `tests/unit/database/conftest.py` -- possibly extend MockBackend if needed (to simulate untranslated words)

**FORBIDDEN -- this task must NEVER touch:**
- Any other module's code or tests
- `nl_processing/database/backend/` files
- `nl_processing/database/exercise_progress.py`
- Integration or e2e tests
- `vulture_whitelist.py`

**Test scope:**
- Verification command: `make check`
- New tests go in: `tests/unit/database/test_service.py`

## Touched surface (expected files / modules)

- `nl_processing/database/service.py` -- ~10 lines added to `get_words()`
- `tests/unit/database/test_service.py` -- ~15 lines added (new test function)
- `tests/unit/database/conftest.py` -- possibly minor change for test setup (may not be needed if existing MockBackend already supports the scenario)

## Dependencies and sequencing notes

- No dependencies. Can run in parallel with T1 and T2.
- No file overlap with other parallel tasks.

## Third-party / library research (mandatory for any external dependency)

N/A -- uses the existing `get_logger` from `nl_processing.database.logging`. Standard Python `logging` module.

## Implementation steps (developer-facing)

1. **Understand the detection approach:**
   The backend `get_user_words()` query uses an INNER JOIN with the translations table, so untranslated words are excluded from results. To detect missing translations, we need to know how many words the user has total vs. how many came back with translations.

   The simplest approach: after `get_user_words()` returns, if the caller did NOT specify `limit` or `random` (which would naturally reduce the count), we can add a lightweight count of the user's total word associations. However, this adds a query.

   **Simpler approach (chosen):** Add a backend method or reuse existing data. Looking at the current code, `get_user_words()` already does the INNER JOIN. We don't have a separate count of untranslated words.

   **Pragmatic solution:** Log the warning at the service level by checking if the returned count is 0 when no filters were applied, or more robustly, add a simple count query to the backend for user words (without the translation join). However, to minimize changes, we can use an approach that doesn't require a new backend method:

   The cleanest FR21-compliant approach: after calling `get_user_words()`, if results are returned and the user has words, log a warning only when we can detect the gap. Since the backend returns only translated pairs (via INNER JOIN), we need a way to know the total.

   **Final approach:** Add a private helper `_count_user_words` call to the backend. The `NeonBackend` already has `add_user_word` which inserts into `user_words` table. We add a lightweight count query. But wait -- we cannot touch backend files (FORBIDDEN for this task to keep it focused).

   **Revised approach (no backend changes):** We can detect this at the service level by checking if any of the words we added (tracked via `add_words`) are missing translations. But `get_words()` doesn't know about recently added words.

   **Simplest viable approach:** Log a debug-level statement with the count returned, and a warning when the returned count is 0 but the user likely has words. This is too vague.

   **Pragmatic compromise:** The INNER JOIN behavior means untranslated words are silently dropped. FR21 says to log a warning. The most practical implementation: after `get_words()` returns pairs from the backend, we can't know the total without a count query. So we should relax the boundary to allow adding a trivial count method to the abstract backend, OR we accept a simpler heuristic.

   **Decision:** Allow touching `abstract.py` and `neon.py` to add a `count_user_words` method. The task boundary constraint is updated below.

   Actually, looking more carefully: the `testing.py` module already has a `count_user_words()` function, but it creates its own backend and is test-only. We need a backend-level method.

   **Simpler alternative that requires NO backend changes:** Add the count query directly inside `service.py` using the existing `self._backend` connection. We can call `self._backend.get_user_words()` with no translation join... but wait, `get_user_words()` already does the JOIN. There's no "unjoined" variant.

   **Final decision:** The simplest correct implementation is to have `get_words()` make a second lightweight query to count total user-word associations (without the translation join). This requires adding a `count_user_words` method to the abstract backend. Update the boundary constraints accordingly.

2. **Add `count_user_words` to `nl_processing/database/backend/abstract.py`:**
   ```python
   @abstractmethod
   async def count_user_words(
       self,
       user_id: str,
       language: str,
       word_type: str | None = None,
   ) -> int:
       """Count user-word associations (without requiring translations)."""
   ```

3. **Add `count_user_words` SQL to `nl_processing/database/backend/_queries.py`:**
   ```python
   def count_user_words_query(language: str, word_type: str | None) -> str:
       query = f"""
           SELECT COUNT(*) AS cnt
           FROM user_words uw
           JOIN words_{language} sw ON uw.word_id = sw.id
           WHERE uw.user_id = $1 AND uw.language = $2
       """
       if word_type is not None:
           query += " AND sw.word_type = $3"
       return query
   ```

4. **Implement `count_user_words` in `nl_processing/database/backend/neon.py`:**
   ```python
   async def count_user_words(
       self,
       user_id: str,
       language: str,
       word_type: str | None = None,
   ) -> int:
       conn = await self._connect()
       query = count_user_words_query(language, word_type)
       args: list[str] = [user_id, language]
       if word_type is not None:
           args.append(word_type)
       try:
           row = await conn.fetchrow(query, *args)
       except asyncpg.PostgresError as exc:
           raise DatabaseError(str(exc)) from exc
       return int(row["cnt"])  # type: ignore[index]
   ```

5. **Update `nl_processing/database/service.py`** method `get_words()`:
   After the existing `pairs` list is built, add:
   ```python
   total_count = await self._backend.count_user_words(
       self._user_id,
       self._source_language.value,
       word_type=word_type.value if word_type else None,
   )
   if total_count > len(pairs):
       _logger.warning(
           "%d of %d words excluded from get_words() due to missing translations",
           total_count - len(pairs),
           total_count,
       )
   ```
   Important: only do this comparison when `limit` is None and `random` is False, because those parameters naturally reduce the result count. If `limit` or `random` is used, the count comparison is meaningless, so skip the warning.

   Revised logic:
   ```python
   if limit is None and not random:
       total_count = await self._backend.count_user_words(
           self._user_id,
           self._source_language.value,
           word_type=word_type.value if word_type else None,
       )
       if total_count > len(pairs):
           _logger.warning(
               "%d of %d words excluded from get_words() due to missing translations",
               total_count - len(pairs),
               total_count,
           )
   ```

6. **Update `tests/unit/database/conftest.py`** -- add `count_user_words` to `MockBackend`:
   ```python
   async def count_user_words(
       self,
       user_id: str,
       language: str,
       word_type: str | None = None,
   ) -> int:
       count = 0
       for uid, wid, lang in self._user_words:
           if uid != user_id or lang != language:
               continue
           if word_type is not None:
               src = self._find_word_by_id(language, wid)
               if src is None or src["word_type"] != word_type:
                   continue
           count += 1
       return count
   ```

7. **Add unit test to `tests/unit/database/test_service.py`:**
   ```python
   @pytest.mark.asyncio
   async def test_get_words_logs_warning_for_untranslated(
       db_service: DatabaseService, mock_backend: MockBackend, caplog: pytest.LogCaptureFixture
   ) -> None:
       """FR21: missing translations logged as warning."""
       # Add word without triggering translation (add directly to backend)
       await mock_backend.add_word("nl", "fiets", "noun")
       await mock_backend.add_user_word("u1", 1, "nl")
       # No translation link exists, so get_words returns empty
       import logging
       with caplog.at_level(logging.WARNING, logger="nl_processing.database.service"):
           pairs = await db_service.get_words()
       assert pairs == []
       assert "excluded from get_words()" in caplog.text
       assert "1 of 1" in caplog.text
   ```

8. **Update `vulture_whitelist.py`:**
   - Add `AbstractBackend.count_user_words  # type: ignore[misc]` after existing entries.
   - Add `NeonBackend.count_user_words  # type: ignore[misc]` after existing entries.

9. **Run `make check`** and confirm 100% green.

## Updated module boundary constraints

**ALLOWED -- this task may ONLY touch:**
- `nl_processing/database/service.py` -- add warning log in `get_words()`
- `nl_processing/database/backend/abstract.py` -- add `count_user_words` abstract method
- `nl_processing/database/backend/neon.py` -- implement `count_user_words`
- `nl_processing/database/backend/_queries.py` -- add count query
- `tests/unit/database/test_service.py` -- add unit test for the warning
- `tests/unit/database/conftest.py` -- add `count_user_words` to MockBackend
- `vulture_whitelist.py` -- add whitelist entries for new method

**FORBIDDEN -- this task must NEVER touch:**
- Any other module's code or tests
- `nl_processing/database/exercise_progress.py`
- Integration or e2e tests

## Production safety constraints (mandatory)

- **Database operations**: The new `count_user_words` query is a read-only SELECT COUNT. It runs only when `limit` is None and `random` is False. It targets the same database the code already connects to.
- **Resource isolation**: Uses existing connection. No new resources.
- **Migration preparation**: N/A -- no schema changes. The query reads from existing `user_words` and `words_{lang}` tables.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Reuses existing backend connection and query pattern.
- **Correct libraries only**: Standard `logging` module, existing `asyncpg`.
- **Correct file locations**: All changes in existing module files.
- **No regressions**: The warning is additive (log only). It does not change return values or behavior. All existing tests pass because the MockBackend will return consistent counts.

## Error handling + correctness rules (mandatory)

- If `count_user_words` fails, the `DatabaseError` will propagate. This is acceptable -- it matches existing behavior where backend failures surface as `DatabaseError`.
- The warning is logged, not raised -- it does not affect the return value of `get_words()`.

## Zero legacy tolerance rule (mandatory)

- No legacy paths. This is a new feature addition per FR21.

## Acceptance criteria (testable)

1. When `get_words()` returns fewer pairs than the user's total word count (and `limit`/`random` are not used), a WARNING is logged.
2. The warning message includes the count of excluded words and total words.
3. When all words have translations, no warning is logged.
4. When `limit` or `random` is specified, no count comparison is performed (no spurious warnings).
5. Unit test verifies the warning using `caplog`.
6. `make check` is 100% green.

## Verification / quality gates

- [ ] `count_user_words` abstract method added to `AbstractBackend`
- [ ] `count_user_words` implemented in `NeonBackend`
- [ ] `count_user_words_query` added to `_queries.py`
- [ ] `get_words()` in `service.py` logs warning for missing translations
- [ ] MockBackend updated with `count_user_words`
- [ ] Unit test verifies warning logging
- [ ] `vulture_whitelist.py` updated
- [ ] `make check` passes
- [ ] All modified files remain under 200 lines
- [ ] No new warnings introduced (other than the intentional FR21 warning)

## Edge cases

- **All words translated**: no warning logged.
- **No words at all**: `count_user_words` returns 0, `len(pairs)` is 0 -- no warning.
- **limit specified**: count check skipped entirely.
- **random=True**: count check skipped entirely.
- **word_type filter**: count uses same filter, so comparison is apples-to-apples.

## Notes / risks

- **Risk**: `service.py` currently 157 lines. Adding ~10 lines brings it to ~167. Within the 200-line limit.
- **Risk**: `neon.py` currently 190 lines. Adding ~12 lines for `count_user_words` could push it to ~202 lines.
  - **Mitigation**: The `_infer_target_language` helper (lines 183-190) could be moved to a shared location, or the count method kept very compact. Monitor closely -- if the file exceeds 200 lines, extract `_infer_target_language` to `_queries.py` or a small utility.
- **Risk**: The extra count query adds latency to `get_words()` when called without `limit` and `random=False`.
  - **Mitigation**: This is the non-hot-path read scenario per NFR1 ("database is optimized for durable remote correctness, not for interactive sub-200ms user-facing reads"). Acceptable.
