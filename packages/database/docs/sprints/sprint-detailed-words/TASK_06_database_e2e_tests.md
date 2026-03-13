---
Task ID: `T6`
Title: `Add e2e tests for full DetailedWordStore flow`
Sprint: `2026-03-13_detailed-words`
Module: `database`
Depends on: `T5`
Parallelizable: `yes, with T7`
---

## Goal / value

Validate the full `DetailedWordStore` lifecycle against a real Neon database: persist source words, store details, retrieve details, and verify get-or-extract read-through behavior. After this task, the database-side detailed-word feature is fully tested end-to-end.

## Context (contract mapping)

- Requirements: `packages/database/docs/module-spec.md` -- FR-11 through FR-14, AC-7, AC-8
- Testing strategy: E2E tests with real Neon database and fake extractor

## Preconditions

- T5 completed: `DetailedWordStore` public API exists.
- T3 completed: `create_tables()` creates `word_details_<src>_<tgt>` table.
- T7 either completed or in-progress (T6 can start before T7 since e2e conftest can handle table drops inline).

## Non-goals

- No real LLM extractor -- use a fake extractor that returns predetermined records.
- No cache-layer testing (that's T9).
- No modification to existing e2e test files.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `tests/e2e/database/` -- new test file(s)

**FORBIDDEN -- this task must NEVER touch:**
- Any source code files
- Any existing test files
- `src/nl_processing/core/` or any core package file

**Test scope:**
- Tests go in: `tests/e2e/database/`
- Test command: `make check` (in `packages/database/`)

## Touched surface (expected files / modules)

**New files to create:**
- `tests/e2e/database/test_detailed_words.py` (~100-150 lines) -- E2E test file

## Dependencies and sequencing notes

- Depends on T5 (store exists) and T3 (table creation works).
- Parallel with T7 (testing helpers).
- The existing `db_ready` fixture in `conftest.py` resets tables. The `word_details_nl_ru` table is now created by `create_tables()` thanks to T3, so it will be available.
- **IMPORTANT**: The existing `drop_all_tables()` in `testing.py` does NOT yet know about `word_details_nl_ru`. If T7 is not done yet, the e2e tests should handle this by either:
  - Adding an inline drop for `word_details_nl_ru` in the test setup, or
  - Relying on `CREATE TABLE IF NOT EXISTS` and UUID-based data isolation.
  - Recommended: Use UUID-based word forms for data isolation (no need to drop the table).

## Third-party / library research (mandatory for any external dependency)

- No new dependencies. Uses existing `asyncpg`, `pytest`, and `pytest_asyncio`.

## Implementation steps (developer-facing)

1. **Create `tests/e2e/database/test_detailed_words.py`:**

   Define a `FakeExtractor` class that implements `DetailedWordExtractorPort`:
   ```python
   class FakeExtractor:
       def __init__(self) -> None:
           self.call_count = 0

       async def extract(self, words: list[Word]) -> list[DetailedWordRecord]:
           self.call_count += 1
           return [
               DetailedWordRecord(
                   source_word=w.normalized_form,
                   word_type=w.word_type.value,
                   schema_key=f"nl_ru_{w.word_type.value}",
                   schema_version=1,
                   payload={"example": f"Detail for {w.normalized_form}"},
               )
               for w in words
           ]
   ```

   Test cases (all use `db_ready` fixture for real Neon):

   - **Test full flow: add word -> store detail -> retrieve detail**:
     1. Create a `DatabaseService` and add a source word (e.g., unique UUID-based form).
     2. Create a `DetailedWordStore` with the same backend.
     3. Call `get_or_extract_details([word])` with `FakeExtractor`.
     4. Verify the record is returned with correct fields.
     5. Call `get_details([word])` -- verify same record is returned from persistence.
     6. Verify `FakeExtractor.call_count == 1` (extracted only once).

   - **Test get_or_extract is read-through** (second call reuses persisted data):
     1. Call `get_or_extract_details` twice for the same word.
     2. Verify extractor called only once.

   - **Test missing source word raises SourceWordNotFoundError**:
     1. Create `DetailedWordStore`.
     2. Call `get_details` for a word NOT in the corpus.
     3. Verify `SourceWordNotFoundError` is raised.

   - **Test multiple words with mixed hit/miss**:
     1. Add two words. Store details for only one.
     2. Call `get_or_extract_details` for both.
     3. Verify extractor called with only the miss.
     4. Verify both records returned in order.

2. **Run `make check`** in `packages/database/` and verify green.

## Production safety constraints (mandatory)

- **Database operations**: E2E tests run against the testing Neon database only (via `DATABASE_URL` from Doppler).
- Uses existing `db_ready` fixture with advisory locks.
- Uses UUID-based word forms for data isolation.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follow the exact e2e test patterns from `test_word_addition_flow.py` and `test_exercise_progress.py`.
- **No regressions**: No existing files modified.

## Error handling + correctness rules (mandatory)

- Tests explicitly assert on specific exception types (`SourceWordNotFoundError`).
- No blanket `except Exception` in test code.

## Zero legacy tolerance rule (mandatory)

- N/A -- this task creates new test code only.

## Acceptance criteria (testable)

1. E2E test file exists at `tests/e2e/database/test_detailed_words.py`.
2. Full flow test passes: add word -> extract details -> retrieve details.
3. Read-through test passes: extractor called only once for the same word.
4. Missing-word test passes: `SourceWordNotFoundError` raised.
5. Mixed hit/miss test passes: only misses trigger extraction.
6. `make check` passes in `packages/database/`.
7. Test file under 200 lines.

## Verification / quality gates

- [x] E2E tests added covering full lifecycle
- [x] Linters/formatters pass (`make check`)
- [x] No new warnings introduced
- [x] Test file under 200 lines
- [x] Error-path test (missing word)

## Edge cases

- Word added but not yet translated (no translation link): `DetailedWordStore` should still work since it operates on canonical words, not translated pairs.
- Concurrent test runs: UUID-based word forms prevent data collision.

## Notes / risks

- **Risk**: E2E tests depend on T7's `drop_all_tables()` update for clean state.
  - **Mitigation**: Use UUID-based word forms for data isolation. The `db_ready` fixture's `reset_database` will create the `word_details_nl_ru` table (via T3's `create_tables()` update). Even if old rows exist, UUID-based forms ensure no collision.
