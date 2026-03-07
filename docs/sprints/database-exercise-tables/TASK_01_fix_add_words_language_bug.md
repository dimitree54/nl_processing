---
Task ID: `T1`
Title: `Fix add_words to use word.language for storage table`
Sprint: `2026-03-07_database-exercise-tables`
Module: `database`
Depends on: `—`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Fix the pre-existing bug where `DatabaseService.add_words()` always stores words in the `source_table` (defaulting to `"nl"`) regardless of the word's actual `language` attribute. After this task, a word with `language=Language.RU` must be stored in `words_ru` and associated via `user_words` with `language="ru"`.

## Context (contract mapping)

- Requirements: Sprint request item 5 — "Pre-existing Test Failure (MUST FIX)"
- Test: `tests/unit/database/test_service.py::test_add_words_uses_word_language_for_storage` — currently FAILING
- The test adds `_DOM = Word(normalized_form="dom", word_type=PartOfSpeech.NOUN, language=Language.RU)` and asserts it's stored in `words_ru` and associated with `language="ru"`.

## Preconditions

- None (this is the first task).

## Non-goals

- Changing any other method on `DatabaseService`.
- Changing the constructor or any interface signatures.
- Touching exercise progress code.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/database/service.py` — fix the `add_words` method
- `tests/unit/database/test_service.py` — verify the fix (test already exists, should now pass)

**FORBIDDEN — this task must NEVER touch:**
- Any other module's code or tests
- `nl_processing/sampling/`
- `nl_processing/core/`
- Tests outside `tests/unit/database/`

**Test scope:**
- Tests go in: `tests/unit/database/`
- Test command: `uv run pytest tests/unit/database/test_service.py -x -v`

## Touched surface (expected files / modules)

- `nl_processing/database/service.py` — lines 70–80 in `add_words()`

## Dependencies and sequencing notes

- No dependencies. This is the first task because it fixes a pre-existing failure that blocks `make check`.
- All subsequent tasks depend on this fix being in place.

## Implementation steps (developer-facing)

1. Open `nl_processing/database/service.py`, method `add_words()` (line 59).
2. Currently, line 72 uses `table = self._source_table` for all words. Change this to use the word's own language:
   ```python
   table = word.language.value
   ```
3. Similarly, line 80 uses `self._source_language.value` for the user-word language association. Change to:
   ```python
   await self._backend.add_user_word(self._user_id, word_id, word.language.value)
   ```
4. Run the failing test to confirm it now passes:
   ```
   uv run pytest tests/unit/database/test_service.py::test_add_words_uses_word_language_for_storage -x -v
   ```
5. Run all unit tests to confirm no regressions:
   ```
   uv run pytest tests/unit/database/ -x -v
   ```
6. Verify file stays under 200 lines: `wc -l nl_processing/database/service.py` (currently 150).

## Production safety constraints (mandatory)

- **Database operations**: This task changes no SQL, no DDL. It changes the Python logic for which table name is passed to the backend. Unit tests use `MockBackend` — no real DB connection.
- **Resource isolation**: No external resources accessed. Unit tests only.
- **Migration preparation**: N/A — no schema changes.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Reuses existing `word.language.value` attribute — no new code paths.
- **Correct file locations**: Only modifies existing file in its current location.
- **No regressions**: The fix makes the failing test pass. Existing passing tests must continue to pass — verify by running the full unit test suite for the module.

## Error handling + correctness rules (mandatory)

- No error handling changes needed. The fix is a data-routing correction (table selection).
- No new error paths introduced.

## Zero legacy tolerance rule (mandatory)

- The hardcoded `self._source_table` usage in `add_words` is the bug. After this fix, the word's own language determines storage location. No dead code left.

## Acceptance criteria (testable)

1. `uv run pytest tests/unit/database/test_service.py::test_add_words_uses_word_language_for_storage -x -v` passes.
2. `uv run pytest tests/unit/database/ -x -v` — all tests pass (zero failures).
3. `nl_processing/database/service.py` remains ≤ 200 lines.
4. `uv run ruff check nl_processing/database/service.py` — no errors.

## Verification / quality gates

- [x] Unit tests added/updated — existing test now passes
- [ ] Integration/e2e tests updated — N/A (unit-level fix)
- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] Negative-path tests exist — the existing test covers the positive case; no new negative paths needed

## Edge cases

- A word list containing mixed languages (e.g., NL and RU words in the same call): each word must be stored under its own language's table. The existing test covers the RU case; the other tests already cover NL.
- Empty word list: already handled (returns early).

## Notes / risks

- **Risk**: The `_translate_and_store` method (line 87) stores translations in `self._target_table`. This is correct because translations are always stored in the target language table. No change needed there.
- **Risk**: Changing storage table for `add_words` could affect `get_words` which joins via `user_words.language`. Since `add_user_word` now also uses `word.language.value`, the join remains consistent.
