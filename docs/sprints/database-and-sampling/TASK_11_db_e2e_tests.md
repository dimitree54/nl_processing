---
Task ID: `T11`
Title: `E2e tests for database module with real translation flow`
Sprint: `2026-03-04_database-and-sampling`
Module: `database`
Depends on: `T10`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

E2e tests exercise the complete database module against a real Neon database with real translation via `translate_word`. These are the primary quality gate: add Dutch words → translations appear → user word lists work → exercise scores persist.

## Context (contract mapping)

- Requirements: `nl_processing/database/docs/prd_database.md` — NFR10-NFR13 (e2e test requirements)
- Architecture: `nl_processing/database/docs/architecture_database.md` — E2E Test Scenarios 1-8

## Preconditions

- T10 complete (integration tests confirm DB operations work)
- T8 complete (testing utilities for setup/teardown)
- All database module code complete (T2-T7)
- Doppler `dev` environment has both `DATABASE_URL` and `OPENAI_API_KEY` (needed for real translation)

## Non-goals

- No mocking — everything is real
- No performance optimization — correctness only (latency already tested in T10)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**

- `tests/e2e/database/` — create directory + test files
- `tests/e2e/database/__init__.py` — create (empty)
- `tests/e2e/database/conftest.py` — create (reset_database setup, drop_all_tables teardown)
- `tests/e2e/database/test_word_addition_flow.py` — scenarios 2, 3
- `tests/e2e/database/test_user_word_lists.py` — scenarios 4, 5
- `tests/e2e/database/test_untranslated_words.py` — scenario 6
- `tests/e2e/database/test_exercise_progress.py` — scenario 8

**FORBIDDEN — this task must NEVER touch:**

- Any module source code
- Tests for other modules
- Production database

**Test scope:**

- Tests go in: `tests/e2e/database/`
- Test command: `doppler run -- uv run pytest -n auto tests/e2e` (runs as part of `make check`)
- Requires both `DATABASE_URL` and `OPENAI_API_KEY` from Doppler

## Touched surface (expected files / modules)

- `tests/e2e/database/__init__.py` (new, empty)
- `tests/e2e/database/conftest.py` (new)
- `tests/e2e/database/test_word_addition_flow.py` (new)
- `tests/e2e/database/test_user_word_lists.py` (new)
- `tests/e2e/database/test_untranslated_words.py` (new)
- `tests/e2e/database/test_exercise_progress.py` (new)

## Dependencies and sequencing notes

- Depends on T10 (integration tests confirm DB basics work)
- No downstream dependencies — this is the final database test layer

## Third-party / library research (mandatory for any external dependency)

- **Library**: pytest-asyncio — `@pytest.mark.asyncio`
- **Service**: Neon PostgreSQL (dev) — via `DATABASE_URL`
- **Service**: OpenAI API — via `OPENAI_API_KEY` (for real `translate_word` calls)
- **Internal**: `nl_processing.translate_word.service.WordTranslator` — called internally by `DatabaseService.add_words`

## Implementation steps (developer-facing)

1. **Create `tests/e2e/database/` directory with `__init__.py` (empty).**

2. **Create `tests/e2e/database/conftest.py`:**
   - Async session-scoped fixture: `reset_database(["nl", "ru"], [("nl", "ru")])` at start
   - Async session-scoped teardown: `drop_all_tables(["nl", "ru"], [("nl", "ru")])` at end
   - Per architecture: "E2e tests always start with reset_database() in setup and drop_all_tables() in teardown"

3. **Create `tests/e2e/database/test_word_addition_flow.py` (scenarios 2 & 3):**
   - Test: Add a batch of real Dutch words → verify they appear in `words_nl` (use `count_words`)
   - Test: `add_words` correctly identifies new vs existing → verify `AddWordsResult` fields
   - Test: Add same words again → all reported as existing, no duplicates in table
   - Test: After adding words, wait briefly for async translation → verify translations appear in `words_ru`
   - Test: Verify translation links created in `translations_nl_ru` (use `count_translation_links`)
   - **Note**: Fire-and-forget translation needs time. Use `asyncio.sleep(5)` or a polling loop to wait for translations to complete before asserting.

4. **Create `tests/e2e/database/test_user_word_lists.py` (scenarios 4 & 5):**
   - Test: Add words as user "test_user_1" → verify user-word associations created
   - Test: Add words as user "test_user_2" (some overlapping) → each user sees only their words
   - Test: Shared corpus contains all words from both users
   - Test: `get_words(word_type=PartOfSpeech.NOUN)` returns only nouns
   - Test: `get_words(limit=3, random=True)` returns exactly 3 unique pairs
   - Test: `get_words()` returns all translated pairs

5. **Create `tests/e2e/database/test_untranslated_words.py` (scenario 6):**
   - Test: Add new words → immediately call `get_words()` → verify untranslated words excluded
   - Test: Verify warning is logged for excluded words (use `caplog` fixture)
   - Test: Wait for translation → call `get_words()` again → verify all words now returned

6. **Create `tests/e2e/database/test_exercise_progress.py` (scenario 8):**
   - Test: Increment scores (+1/-1) for a subset of words
   - Test: Verify score persistence via `get_word_pairs_with_scores`
   - Test: Score-aware retrieval returns expected per-exercise scores

7. **200-line limit per file**: 4 test files, each focused on a scenario group. Stay under 200 lines each.

8. Run `doppler run -- make check` — all e2e tests must pass.

## Production safety constraints (mandatory)

- **Database operations**: All against dev Neon database. `doppler run --` ensures `DATABASE_URL` points to dev.
- **API calls**: Real OpenAI API calls for translation. Costs real money but is required (integration tests are the quality gate).
- **Resource isolation**: Dev database only. Production database never accessible.
- **Cleanup**: `drop_all_tables` in teardown ensures dev database left clean.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Uses testing utilities from T8.
- **No regressions**: New test files only.

## Error handling + correctness rules (mandatory)

- Tests must not swallow assertion errors.
- Real API failures → test fails (not silenced).
- Translation timeout → explicit `asyncio.sleep` or polling, not infinite wait.

## Zero legacy tolerance rule (mandatory)

- No old test files.

## Acceptance criteria (testable)

1. `tests/e2e/database/` directory exists with conftest and 4 test files.
2. All test files under 200 lines.
3. E2e tests use real Neon database and real OpenAI translation.
4. Word addition flow: adds, deduplicates, triggers translation.
5. User word lists: multi-user isolation, filtering.
6. Untranslated word exclusion with logging.
7. Exercise progress: increment, persist, read.
8. Dev database left clean after tests.
9. `make check` passes.

## Verification / quality gates

- [ ] 4 e2e test files created
- [ ] conftest has reset/teardown
- [ ] All tests pass with real DB + real translation
- [ ] Dev database clean after run
- [ ] All files under 200 lines
- [ ] `make check` passes

## Edge cases

- Translation may take 3-10 seconds — poll or sleep with generous timeout.
- OpenAI rate limits — keep test word counts small (5-10 words per test).
- pytest-xdist may run e2e tests in parallel — use unique user IDs per test file to avoid conflicts.

## Notes / risks

- **Risk**: Translation timing makes tests flaky.
  - **Mitigation**: Use polling with timeout (max 15s) instead of fixed sleep. Assert after polling confirms translation exists.
- **Risk**: OpenAI API costs.
  - **Mitigation**: Use minimal word sets (5-10 words). This matches existing e2e test patterns in the project.
- **Risk**: pytest-xdist parallel execution causes DB conflicts.
  - **Mitigation**: Each test file uses unique user_id prefixes. conftest uses session-scoped setup.
