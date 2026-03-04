---
Task ID: `T8`
Title: `Create database testing utilities (testing.py)`
Sprint: `2026-03-04_database-and-sampling`
Module: `database`
Depends on: `T5`
Parallelizable: `yes, with T6 and T7`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Test utility functions (`drop_all_tables`, `reset_database`, `count_words`, `count_user_words`, `count_translation_links`) are available for integration and e2e tests. These live in `testing.py` — separate from production code, never imported by production modules.

## Context (contract mapping)

- Requirements: `nl_processing/database/docs/prd_database.md` — FR23-FR27 (testing utilities)
- Architecture: `nl_processing/database/docs/architecture_database.md` — Backdoor / Test Utility Functions section, testing.py

## Preconditions

- T5 complete (NeonBackend and DatabaseService available)
- T4 complete (NeonBackend for direct DB operations)

## Non-goals

- No tests of the testing utilities themselves (they are tested implicitly by T10/T11)
- Not production code — clearly documented

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**

- `nl_processing/database/testing.py` — create

**FORBIDDEN — this task must NEVER touch:**

- `nl_processing/database/service.py`
- `nl_processing/database/__init__.py`
- Any other module's code or tests

**Test scope:**

- No new tests — these utilities are the foundation for tests in T10/T11
- `make check` must pass

## Touched surface (expected files / modules)

- `nl_processing/database/testing.py` (new)

## Dependencies and sequencing notes

- Depends on T5 (NeonBackend pattern)
- T10 (integration tests) and T11 (e2e tests) depend on this
- Can run in parallel with T6 and T7

## Third-party / library research (mandatory for any external dependency)

- No new dependencies — uses asyncpg via NeonBackend.

## Implementation steps (developer-facing)

1. **Create `nl_processing/database/testing.py`:**

2. **Implement utility functions** (all async, all use `NeonBackend` under the hood):

   **`drop_all_tables(languages: list[str], pairs: list[tuple[str, str]]) -> None`**:
   - Drops `user_word_exercise_scores_{src}_{tgt}` for each pair
   - Drops `translations_{src}_{tgt}` for each pair
   - Drops `user_words` table
   - Drops `words_{lang}` for each language
   - Uses `DROP TABLE IF EXISTS` — safe to call even if tables don't exist
   - Drops in correct order to respect foreign key constraints (exercise scores → translations → user_words → word tables)
   - **Warning**: This is irreversible — documented in docstring

   **`reset_database(languages: list[str], pairs: list[tuple[str, str]]) -> None`**:
   - Calls `drop_all_tables(languages, pairs)`
   - Calls `backend.create_tables(languages, pairs)` (NeonBackend method from T4)
   - Result: clean database with empty tables

   **`count_words(table: str) -> int`**:
   - `SELECT COUNT(*) FROM words_{table}` — returns integer count

   **`count_user_words(user_id: str, language: str) -> int`**:
   - `SELECT COUNT(*) FROM user_words WHERE user_id = $1 AND language = $2`

   **`count_translation_links(table: str) -> int`**:
   - `SELECT COUNT(*) FROM translations_{table}`

3. **Each function** reads `os.environ["DATABASE_URL"]` internally and creates a temporary `NeonBackend`. This is a testing utility — performance of setup/teardown is not critical.

4. **Docstrings**: Each function has a clear docstring stating it's for test use only and should never be imported by production code.

5. Run `make check`.

## Production safety constraints (mandatory)

- **Database operations**: These functions WILL execute SQL when called. They are designed to be called ONLY against the dev database via `doppler run --`.
- **Resource isolation**: Functions read `DATABASE_URL` from environment. When run via `doppler run -- make check`, this points to the dev Neon database. Production database is NEVER accessible during test runs.
- **CRITICAL**: `drop_all_tables` is irreversible. It MUST only be called in test contexts (dev database).

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Uses NeonBackend for SQL execution — no raw asyncpg calls.
- **Correct file locations**: `testing.py` per architecture doc.
- **No regressions**: New file only, not imported by any existing code.

## Error handling + correctness rules (mandatory)

- If database is unreachable, `DatabaseError` propagates (no silent fallback).
- `DROP TABLE IF EXISTS` prevents errors when tables don't exist.

## Zero legacy tolerance rule (mandatory)

- No old code paths affected.

## Acceptance criteria (testable)

1. `nl_processing/database/testing.py` defines all 5 utility functions.
2. All functions are `async def`.
3. `drop_all_tables` drops tables in FK-respecting order.
4. `reset_database` drops and recreates tables.
5. Count functions return integers.
6. File is under 200 lines.
7. File has clear docstrings marking it as test-only.
8. `make check` passes.

## Verification / quality gates

- [ ] All 5 functions implemented
- [ ] Functions use NeonBackend for SQL
- [ ] DROP order respects FK constraints
- [ ] File under 200 lines
- [ ] `make check` passes

## Edge cases

- `drop_all_tables` called when tables don't exist — `IF EXISTS` handles this.
- `count_words` on empty table — returns 0.
- `reset_database` called twice — second call is idempotent (IF NOT EXISTS on create).

## Notes / risks

- **Risk**: Testing utilities accidentally imported in production code.
  - **Mitigation**: File named `testing.py` with explicit docstrings. vulture or import analysis can catch production imports.
