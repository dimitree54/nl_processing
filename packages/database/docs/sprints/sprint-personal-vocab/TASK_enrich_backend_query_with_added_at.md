---
Task ID: `T1`
Title: `Add added_at to backend get_user_words query and propagate through backend layer`
Sprint: `2026-03-12_personal-vocab`
Module: `database`
Depends on: `—`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

The `get_user_words` SQL query and backend method must return the `uw.added_at` column from the `user_words` table so that downstream consumers (FR-7 personal-vocab reads, FR-10 enriched snapshots) can surface this timestamp. This is the foundational change all other tasks depend on.

## Context (contract mapping)

- Requirements: `docs/module-spec.md` — BR-6 (added_at sourced from user_words.added_at), CR-3 (reads and snapshots share field set)
- Module spec: `docs/module-spec.md`

## Preconditions

- `user_words` table already has `added_at TIMESTAMP NOT NULL DEFAULT NOW()` — no schema migration needed.
- `_queries.py` is at 187 lines — adding `uw.added_at` to the SELECT clause will not push it over 200 (it adds ~1 line to an existing query).

## Non-goals

- Creating new public API methods (that is T2/T3).
- File decomposition of `_queries.py` (it stays under 200 with this change).
- Modifying the `get_words()` return type on `DatabaseService` (it uses `WordPair` which doesn't carry `added_at`).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `src/nl_processing/database/backend/_queries.py` — add `uw.added_at` to the SELECT in `get_user_words_query()`
- `tests/unit/database/conftest.py` — update `MockBackend._build_joined_row()` to include `added_at`
- `tests/unit/database/` — any new or updated unit tests
- `tests/integration/database/` — any new or updated integration tests

**FORBIDDEN — this task must NEVER touch:**
- Any `core` package file
- Any other module's code or tests
- Bot code

**Test scope:**
- Tests go in: `tests/unit/database/`, `tests/integration/database/`
- Test command: `make check`
- NEVER run the full monorepo test suite

## Touched surface (expected files / modules)

- `src/nl_processing/database/backend/_queries.py` — modify `get_user_words_query()` to include `uw.added_at AS added_at` in the SELECT clause
- `tests/unit/database/conftest.py` — update `MockBackend._build_joined_row()` to include `"added_at"` key (use a fixed datetime or `datetime.now()` for mock data)
- `tests/integration/database/test_neon_backend.py` — add a test asserting the `added_at` field is present and is a valid timestamp in rows returned by `get_user_words()`

## Dependencies and sequencing notes

- This is the foundation task. No dependencies.
- T2, T3, T4, T5 all depend on this because they consume the enriched row data.

## Third-party / library research (mandatory for any external dependency)

No new external dependencies. The `uw.added_at` column is a standard PostgreSQL `TIMESTAMP` type; `asyncpg` returns it as a Python `datetime.datetime` object. The `MockBackend` will use `datetime.datetime` from the stdlib.

## Implementation steps (developer-facing)

1. **Modify `get_user_words_query()` in `_queries.py`**:
   - Add `uw.added_at AS added_at` to the SELECT column list (after `tw.word_type AS target_word_type`).
   - This is a one-line addition inside the existing f-string. The file goes from 187 to ~188 lines.

2. **Update `MockBackend._build_joined_row()` in `tests/unit/database/conftest.py`**:
   - Add `from datetime import datetime, timezone` import at the top.
   - In `_build_joined_row()`, add `"added_at": datetime.now(tz=timezone.utc)` to the returned dict.
   - This ensures all existing unit tests that consume row dicts continue to work, and new tests can assert on `added_at`.

3. **Add integration test for `added_at` presence**:
   - In `tests/integration/database/test_neon_backend.py`, add a test `test_get_user_words_includes_added_at`:
     - Insert a word, create a translation link, associate with a user.
     - Call `get_user_words()` and assert the returned row dict contains `"added_at"`.
     - Assert the value is a `datetime` instance.

4. **Verify existing tests still pass**:
   - Run `make check`. The added column in the SELECT is purely additive — existing code that reads `source_id`, `source_normalized_form`, etc. from the row dict is unaffected. The `service.py` `get_words()` method indexes specific keys; it will simply ignore `added_at`.

## Production safety constraints (mandatory)

- **Database operations**: Only the SELECT query is modified (adding a column to the output). No writes, no DDL. Testing uses the test Neon DB via Doppler-managed `DATABASE_URL`.
- **Resource isolation**: UUID-based `user_id` isolation in tests. No port or file conflicts.
- **Migration preparation**: N/A — no schema changes.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Extends the existing `get_user_words_query()` function — no new query function created.
- **Correct libraries only**: `datetime` from stdlib, `asyncpg` already in use.
- **Correct file locations**: Changes stay in existing files at their current paths.
- **No regressions**: Existing tests continue to pass because `added_at` is purely additive to the row dict.

## Error handling + correctness rules (mandatory)

- No new error paths introduced. The `added_at` column is `NOT NULL DEFAULT NOW()` — it will always be present for any `user_words` row.
- No `try/catch` changes needed.

## Zero legacy tolerance rule (mandatory)

- No dead code is introduced. No old paths are superseded.

## Acceptance criteria (testable)

1. `get_user_words_query()` SQL includes `uw.added_at AS added_at` in the SELECT clause.
2. `MockBackend._build_joined_row()` returns a dict with an `"added_at"` key containing a `datetime` value.
3. Integration test `test_get_user_words_includes_added_at` passes: real Neon DB returns rows with `added_at` as a `datetime`.
4. All existing unit, integration, and e2e tests continue to pass.
5. `make check` is green (all linters and tests pass).
6. `_queries.py` stays under 200 lines.

## Verification / quality gates

- [ ] Unit tests pass (`tests/unit/database/`)
- [ ] Integration tests pass, including new `added_at` test (`tests/integration/database/`)
- [ ] E2e tests pass (`tests/e2e/database/`)
- [ ] `make check` green (ruff, pylint 200-line limit, all test suites)
- [ ] No new warnings introduced

## Edge cases

- Rows created before `added_at` had a default: Not possible — column has `DEFAULT NOW()` since table creation. All rows have `added_at`.
- `MockBackend` callers accessing `added_at` before `_build_joined_row` is called: No issue — the method always includes it.

## Notes / risks

- **Risk**: `conftest.py` (unit) is at 198 lines — adding `from datetime import datetime, timezone` import pushes it to ~199. If any further additions are needed in this task, consider extracting `MockBackend` into a separate file.
  - **Mitigation**: The import line and one dict key addition are minimal. Monitor the count. If it hits 200 during this task, extract `MockBackend` into `tests/unit/database/mock_backend.py` and re-export from `conftest.py`.
