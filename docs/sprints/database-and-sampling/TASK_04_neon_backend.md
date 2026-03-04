---
Task ID: `T4`
Title: `Implement NeonBackend with asyncpg`
Sprint: `2026-03-04_database-and-sampling`
Module: `database`
Depends on: `T3`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

A concrete `NeonBackend` implementation of `AbstractBackend` that uses `asyncpg` to connect to Neon PostgreSQL and execute all CRUD operations. This is the database module's single production backend.

## Context (contract mapping)

- Requirements: `nl_processing/database/docs/prd_database.md` — NFR15 (asyncpg), NFR1 (200ms latency), NFR9 (connection pooling)
- Architecture: `nl_processing/database/docs/architecture_database.md` — Decision: Neon PostgreSQL as First Backend, Decision: Abstract Backend Interface

## Preconditions

- T3 complete (`AbstractBackend` ABC exists)
- T1 complete (asyncpg is installed)
- T2 complete (exceptions exist for error wrapping)

## Non-goals

- No service-layer logic (that's T5)
- No testing of NeonBackend in this task (deferred to T10)
- No connection to real database yet — just the implementation

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**

- `nl_processing/database/backend/neon.py` — create

**FORBIDDEN — this task must NEVER touch:**

- `nl_processing/database/backend/abstract.py` (already complete)
- `nl_processing/database/backend/__init__.py` (must stay empty)
- Any other module's code or tests
- `nl_processing/database/service.py`

**Test scope:**

- No new tests (integration testing in T10)
- `make check` must pass with existing 26 tests

## Touched surface (expected files / modules)

- `nl_processing/database/backend/neon.py` (new)

## Dependencies and sequencing notes

- Depends on T3 (AbstractBackend ABC)
- T5 (DatabaseService) depends on this

## Third-party / library research (mandatory for any external dependency)

- **Library/API**: asyncpg 0.31.0
- **Official documentation**: https://magicstack.github.io/asyncpg/current/
- **API reference**: https://magicstack.github.io/asyncpg/current/api/index.html
- **Key methods used**:
  - `asyncpg.connect(dsn=...)` — single connection: https://magicstack.github.io/asyncpg/current/api/index.html#asyncpg.connect
  - `connection.execute(query, *args)` — execute SQL: https://magicstack.github.io/asyncpg/current/api/index.html#asyncpg.connection.Connection.execute
  - `connection.fetchrow(query, *args)` — fetch single row: https://magicstack.github.io/asyncpg/current/api/index.html#asyncpg.connection.Connection.fetchrow
  - `connection.fetch(query, *args)` — fetch all rows: https://magicstack.github.io/asyncpg/current/api/index.html#asyncpg.connection.Connection.fetch
  - `asyncpg.Record` — row type (supports dict-like `[]` access): https://magicstack.github.io/asyncpg/current/api/index.html#asyncpg.Record
- **Usage pattern (verified)**:
  ```python
  conn = await asyncpg.connect(dsn=database_url)
  row = await conn.fetchrow("INSERT INTO t (col) VALUES ($1) ON CONFLICT DO NOTHING RETURNING id", value)
  rows = await conn.fetch("SELECT * FROM t WHERE id = $1", id_val)
  await conn.close()
  ```
- **Known gotchas**:
  - asyncpg uses `$1, $2` parameter placeholders (not `%s`)
  - `ON CONFLICT DO NOTHING RETURNING id` returns `None` if conflict (row already exists) — this is how we detect existing words
  - `asyncpg.Record` supports `record['column']` access (bracket notation, project-compatible)
  - Neon serverless may have cold-start latency on first connection — subsequent queries are fast

## Implementation steps (developer-facing)

1. **Create `nl_processing/database/backend/neon.py`:**

2. **Implement `NeonBackend(AbstractBackend)`:**
   - Constructor: `__init__(self, database_url: str)` — store the URL, no connection yet
   - Private `_connect(self)` async method — lazily creates `asyncpg.connect(dsn=self._database_url)` and caches the connection
   - Implement all 8 abstract methods using asyncpg SQL queries:

   **`create_tables`**: For each language, create `words_{lang}` table with `id SERIAL PK`, `normalized_form VARCHAR UNIQUE NOT NULL`, `word_type VARCHAR NOT NULL`. For each pair, create `translations_{src}_{tgt}` with foreign keys. Create `user_words` table. Create `user_word_exercise_scores_{src}_{tgt}` tables. All use `IF NOT EXISTS`.

   **`add_word`**: `INSERT INTO words_{table} (normalized_form, word_type) VALUES ($1, $2) ON CONFLICT (normalized_form) DO NOTHING RETURNING id`. Return the id or None.

   **`get_word`**: `SELECT id, normalized_form, word_type FROM words_{table} WHERE normalized_form = $1`.

   **`add_translation_link`**: `INSERT INTO translations_{table} (source_word_id, target_word_id) VALUES ($1, $2) ON CONFLICT DO NOTHING`.

   **`add_user_word`**: `INSERT INTO user_words (user_id, word_id, language) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING`.

   **`get_user_words`**: Join `user_words` with `words_{lang}` and `translations_{src}_{tgt}` to get translated pairs. Apply optional filters (`word_type`, `limit`, `ORDER BY RANDOM()`).

   **`increment_user_exercise_score`**: `INSERT INTO user_word_exercise_scores_{table} ... ON CONFLICT ... DO UPDATE SET score = score + $4, updated_at = NOW()`. Return new score.

   **`get_user_exercise_scores`**: `SELECT source_word_id, exercise_type, score FROM user_word_exercise_scores_{table} WHERE user_id = $1 AND source_word_id = ANY($2) AND exercise_type = ANY($3)`.

3. **SQL injection safety**: Table names are constructed from `Language.value` strings (controlled enum values like `"nl"`, `"ru"`), NOT from user input. Use parameterized queries for all user-provided values. Note: ruff S608 flags string-formatted SQL — table names must be formatted into queries since asyncpg doesn't support parameterized table names. This is safe because table names come from `Language` enum values, never from user input. Add a `# noqa: S608` comment where necessary, with an inline explanation.

4. **200-line limit awareness**: NeonBackend has 8 methods + constructor + helper. If approaching 200 lines, extract SQL query strings into module-level constants or split helper methods into a separate private module `nl_processing/database/backend/_queries.py`.

5. Run `make check` — verify no lint issues and existing tests pass.

## Production safety constraints (mandatory)

- **Database operations**: No connections made during this task — only implementation code. Connection only happens when methods are called (lazy connect).
- **Resource isolation**: `database_url` is passed as a constructor argument, sourced from `os.environ["DATABASE_URL"]` at the service layer. The env var comes from Doppler — dev environment points to dev database.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Uses asyncpg as specified in architecture. No custom connection pool — asyncpg's single connection for now (architecture mentions internal connection pooling but doesn't specify pool size for v1).
- **Correct libraries only**: asyncpg >=0.30 from pyproject.toml.
- **Correct file locations**: `backend/neon.py` per architecture doc.
- **No regressions**: New file only.

## Error handling + correctness rules (mandatory)

- Wrap `asyncpg` exceptions in `DatabaseError` from `nl_processing.database.exceptions`.
- `ConfigurationError` is NOT raised here — that's the service layer's job (T5).
- Never swallow exceptions — always raise `DatabaseError` with the original message.
- Use structured logging via `nl_processing.database.logging.get_logger` for query debugging.

## Zero legacy tolerance rule (mandatory)

- No old code paths affected.

## Acceptance criteria (testable)

1. `nl_processing/database/backend/neon.py` defines `NeonBackend(AbstractBackend)` implementing all 8 abstract methods.
2. All methods use asyncpg with parameterized queries for user-provided values.
3. Table names are constructed from controlled enum-derived strings only.
4. `create_tables` uses `IF NOT EXISTS` for all table creation.
5. `add_word` returns `int | None` (id or None for duplicate).
6. File is under 200 lines (or split into neon.py + _queries.py, each under 200).
7. `from nl_processing.database.backend.neon import NeonBackend` succeeds.
8. `make check` passes.

## Verification / quality gates

- [ ] NeonBackend implements all AbstractBackend methods
- [ ] Parameterized queries for all user inputs
- [ ] File(s) under 200 lines each
- [ ] ruff format + check passes (S608 noqa if needed for table name formatting, with justification)
- [ ] `make check` passes (26 tests)

## Edge cases

- `ON CONFLICT DO NOTHING RETURNING id` returns no rows (not None) when conflict occurs — use `fetchrow` which returns `None` in this case.
- `get_user_words` with `random=True` and no `limit` — should still work (ORDER BY RANDOM() without LIMIT returns all in random order).
- Empty `source_word_ids` list in `get_user_exercise_scores` — handle gracefully (return empty list, don't execute invalid SQL).

## Notes / risks

- **Risk**: File may exceed 200 lines with 8 methods + SQL.
  - **Mitigation**: Extract SQL into constants or a private helper module. Architecture anticipates this with the modular file structure.
- **Risk**: `# noqa: S608` needed for table name formatting.
  - **Mitigation**: Document clearly in code comments that table names derive from `Language` enum, not user input.
