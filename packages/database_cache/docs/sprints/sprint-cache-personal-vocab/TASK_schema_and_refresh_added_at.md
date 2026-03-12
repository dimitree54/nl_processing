---
Task ID: `T2`
Title: `Add added_at to DDL, persist it in refresh, update tuple handling`
Sprint: `2026-03-12_cache-personal-vocab`
Module: `database_cache`
Depends on: `T1`
Parallelizable: no
---

## Goal / value

The `cached_word_pairs` table gains an `added_at TEXT` column. The `CacheSyncer.refresh()` method extracts `added_at` from `EnrichedWordPairSnapshot` objects and passes it through to `rebuild_snapshot()`. After this task, the local SQLite cache stores `added_at` for every cached word pair, enabling FR-7's `list_personal_words()` in T3.

## Context (contract mapping)

- Requirements: `docs/module-spec.md` — FR-10, CR-3
- Module spec: `docs/module-spec.md` — DEC-2, IF-3
- Related: `database.models.EnrichedWordPairSnapshot` has `added_at: datetime`
- Related: `database.exercise_progress.ExerciseProgressStore.export_remote_snapshot()` returns `list[EnrichedWordPairSnapshot]`

## Preconditions

- T1 (decompose) is complete — `service.py` and `local_store.py` are under 170 lines
- `EnrichedWordPairSnapshot` extends `WordPairSnapshot` with `added_at: datetime` (confirmed in `database.models`)
- `export_remote_snapshot()` already returns `EnrichedWordPairSnapshot` objects (confirmed in `database.exercise_progress`)

## Non-goals

- Implementing `list_personal_words()` (that's T3)
- Implementing delete APIs (that's T5)
- Modifying `RemoteProgressSyncPort` or `EnrichedWordPairSnapshot` (owned by other packages)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `src/nl_processing/database_cache/` — module source code
- `tests/unit/database_cache/` — unit tests
- `tests/integration/database_cache/` — integration tests

**FORBIDDEN — this task must NEVER touch:**
- `src/nl_processing/core/` or any `core` package file
- `src/nl_processing/database/` or any `database` package file
- Any other module's code or tests

**Test scope:**
- Tests go in: `tests/unit/database_cache/`, `tests/integration/database_cache/`
- Test command: `uv run pytest tests/unit/database_cache/ tests/integration/database_cache/ -x -v`
- NEVER run the full test suite or tests from other modules

## Touched surface (expected files / modules)

- `src/nl_processing/database_cache/_local_store_queries.py` — update `DDL_CACHED_WORD_PAIRS` to include `added_at TEXT`, update `INSERT_WORD_PAIR` to accept 7 values
- `src/nl_processing/database_cache/local_store.py` — update `rebuild_snapshot()` signature from 6-element to 7-element tuples
- `src/nl_processing/database_cache/sync.py` — update `refresh()` to extract `added_at` from `EnrichedWordPairSnapshot` and pass 7-element tuples
- `tests/unit/database_cache/conftest.py` — update `make_scored_pair()` to produce `EnrichedWordPairSnapshot` with `added_at` (or keep `WordPairSnapshot` and have `MockProgressStore` wrap it)
- `tests/unit/database_cache/test_sync.py` — update tests to verify `added_at` is persisted
- `tests/unit/database_cache/test_local_store.py` — update `_NOUN_PAIR`, `_VERB_PAIR`, `_ADJ_PAIR` tuples to 7 elements
- `tests/integration/database_cache/conftest.py` — update `make_scored_pair()` to include `added_at`
- `tests/integration/database_cache/test_persistence.py` — update pair tuples to 7 elements; add persistence test for `added_at`
- `tests/integration/database_cache/test_refresh_rebuild.py` — update to verify `added_at` survives refresh

## Dependencies and sequencing notes

- Depends on T1 because the decomposed `local_store.py` must be in place before modifying `rebuild_snapshot()`.
- T3 (list_personal_words) directly depends on the `added_at` column being present.
- T5 (delete) depends on the updated DDL for correct table shape.

## Third-party / library research (mandatory for any external dependency)

No new third-party libraries. `aiosqlite` already handles `TEXT` columns for ISO datetime strings.

**Key technical note**: `EnrichedWordPairSnapshot` is a Pydantic model in `database.models` with `added_at: datetime`. The `export_remote_snapshot()` return type in `RemoteProgressSyncPort` is `list[WordPairSnapshot]`, but the actual runtime objects are `EnrichedWordPairSnapshot` instances (subclass). The code must use `hasattr` or explicit typing to access `added_at` from the returned objects.

**Better approach**: Since `EnrichedWordPairSnapshot` is a subclass of `WordPairSnapshot`, and `export_remote_snapshot()` returns `list[WordPairSnapshot]` per the protocol, the sync code should check `hasattr(sp, 'added_at')` and use a sensible default (e.g., current timestamp) when the attribute is absent. This keeps backward compatibility if a mock or older remote implementation doesn't include `added_at`.

## Implementation steps (developer-facing)

### Step 1: Update DDL in `_local_store_queries.py`

1. Add `added_at TEXT` column to `DDL_CACHED_WORD_PAIRS`:
   ```sql
   CREATE TABLE IF NOT EXISTS cached_word_pairs (
       source_word_id INTEGER PRIMARY KEY,
       source_normalized_form TEXT NOT NULL,
       source_word_type TEXT NOT NULL,
       target_word_id INTEGER NOT NULL,
       target_normalized_form TEXT NOT NULL,
       target_word_type TEXT NOT NULL,
       added_at TEXT
   )
   ```
2. Update `INSERT_WORD_PAIR` to accept 7 values:
   ```python
   INSERT_WORD_PAIR = (
       "INSERT INTO cached_word_pairs "
       "(source_word_id, source_normalized_form, source_word_type, "
       "target_word_id, target_normalized_form, target_word_type, added_at) "
       "VALUES (?, ?, ?, ?, ?, ?, ?)"
   )
   ```

### Step 2: Update `rebuild_snapshot()` in `local_store.py`

1. Change the `word_pairs` parameter type from `list[tuple[int, str, str, int, str, str]]` to `list[tuple[int, str, str, int, str, str, str | None]]` (7th element is `added_at` as ISO string or `None`).
2. The `INSERT_WORD_PAIR` call already passes the full tuple, so no loop body change needed — it just passes 7 values instead of 6.

### Step 3: Update `refresh()` in `sync.py`

1. Import `datetime` handling if not already present.
2. In the list comprehension building `word_pairs`, extract `added_at` from each `sp`:
   ```python
   word_pairs: list[tuple[int, str, str, int, str, str, str | None]] = [
       (
           sp.source_word_id,
           sp.pair.source.normalized_form,
           sp.pair.source.word_type.value,
           sp.target_word_id,
           sp.pair.target.normalized_form,
           sp.pair.target.word_type.value,
           sp.added_at.isoformat() if hasattr(sp, 'added_at') else None,
       )
       for sp in scored_pairs
   ]
   ```

### Step 4: Update unit test fixtures and data

1. In `tests/unit/database_cache/conftest.py`:
   - Update `make_scored_pair()` to return `EnrichedWordPairSnapshot` (from `database.models`) with an `added_at` field. Use a fixed test datetime like `datetime(2025, 1, 15, 12, 0, tzinfo=UTC)`.
   - Update `MockProgressStore.export_remote_snapshot()` return type hint.
2. In `tests/unit/database_cache/test_local_store.py`:
   - Update `_NOUN_PAIR`, `_VERB_PAIR`, `_ADJ_PAIR` to 7-element tuples: `(1, "huis", "noun", 0, "dom", "noun", "2025-01-15T12:00:00+00:00")`.
   - Add a test `test_added_at_persisted_in_snapshot` that verifies `added_at` is stored and retrievable after `rebuild_snapshot()`.
3. In `tests/unit/database_cache/test_sync.py`:
   - Add a test `test_refresh_persists_added_at` that verifies after refresh, `SELECT added_at FROM cached_word_pairs` returns non-null ISO datetime strings.

### Step 5: Update integration test fixtures and data

1. In `tests/integration/database_cache/conftest.py`:
   - Update `make_scored_pair()` to return `EnrichedWordPairSnapshot` with `added_at`.
2. In `tests/integration/database_cache/test_persistence.py`:
   - Update `_PAIR_HUIS`, `_PAIR_BOEK` to 7-element tuples.
   - Add a test `test_added_at_survives_close_reopen` verifying `added_at` persists across SQLite close/reopen cycles.
3. In `tests/integration/database_cache/test_refresh_rebuild.py`:
   - Update `make_scored_pair()` calls (already handled by conftest change).
   - Add assertion in `test_refresh_replaces_snapshot_atomically` that `added_at` is present in refreshed rows.

### Step 6: Run all tests and verify

1. `uv run pytest tests/unit/database_cache/ -x -v` — all pass
2. `uv run pytest tests/integration/database_cache/ -x -v` — all pass
3. Verify line counts are still under 200 for all files.

## Production safety constraints (mandatory)

- **Database operations**: All reads/writes target the **testing/development database only**. SQLite caches use in-memory (`:memory:`) or `tmp_path` files.
- **Schema change**: `CREATE TABLE IF NOT EXISTS` — existing production SQLite files will be rebuilt on next `refresh()` since `rebuild_snapshot()` drops and recreates all rows. The column addition is in the DDL, not a migration.
- **Backward compatibility**: The `hasattr(sp, 'added_at')` guard means old mock objects without `added_at` still work (with `None` stored).

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Reuses existing `rebuild_snapshot()` flow, just grows the tuple.
- **Correct libraries only**: `aiosqlite` (existing), `datetime` (stdlib).
- **No regressions**: Every existing test is updated to use 7-element tuples and must still pass.

## Error handling + correctness rules (mandatory)

- **Do not silence errors**: No error handling changes.
- `added_at` is `TEXT` (nullable) in SQLite — if absent from remote, stored as `NULL`. No silent default.
- The `hasattr` guard in `sync.py` is an explicit compatibility path, not error silencing.

## Zero legacy tolerance rule (mandatory)

After implementing this task:

- The 6-element tuple format is fully replaced by the 7-element format everywhere.
- No code paths remain that produce or consume 6-element tuples.
- Old `INSERT_WORD_PAIR` SQL with 6 placeholders is replaced.

## Acceptance criteria (testable)

1. `DDL_CACHED_WORD_PAIRS` includes `added_at TEXT` column.
2. `INSERT_WORD_PAIR` accepts 7 values including `added_at`.
3. `rebuild_snapshot()` accepts 7-element tuples.
4. `CacheSyncer.refresh()` extracts `added_at` from `EnrichedWordPairSnapshot` and passes it through.
5. Unit test confirms `added_at` is retrievable from SQLite after `rebuild_snapshot()`.
6. Unit test confirms `added_at` is persisted after `refresh()`.
7. Integration test confirms `added_at` survives SQLite close/reopen.
8. All existing tests pass with updated tuple format.
9. All files remain under 200 lines.

## Verification / quality gates

- [ ] Unit tests pass: `uv run pytest tests/unit/database_cache/ -x -v`
- [ ] Integration tests pass: `uv run pytest tests/integration/database_cache/ -x -v`
- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] New negative-path test: `added_at` missing from snapshot object stores `NULL`
- [ ] Line counts verified: all files under 200

## Edge cases

- `EnrichedWordPairSnapshot` returned by `export_remote_snapshot()` has `added_at` as `datetime` — must convert to ISO string for SQLite `TEXT` storage.
- A mock `RemoteProgressSyncPort` that returns plain `WordPairSnapshot` (without `added_at`) — handled by `hasattr` guard, stores `NULL`.
- `added_at` could theoretically be a naive datetime without timezone — the `isoformat()` call handles this; consumers should parse accordingly.
- Existing production SQLite files with the old 6-column schema — `CREATE TABLE IF NOT EXISTS` means the old table persists. However, `rebuild_snapshot()` does `DELETE FROM cached_word_pairs` before `INSERT`, and the `INSERT` now has 7 columns. **This will fail** if the old table only has 6 columns. **Mitigation**: Since the cache is ephemeral and rebuild is destructive, drop and recreate the table during schema setup (in `open()`). Alternatively, use `DROP TABLE IF EXISTS` before `CREATE TABLE` in the DDL. **Decision**: Keep `CREATE TABLE IF NOT EXISTS` but add an `ALTER TABLE` migration check: attempt `ALTER TABLE cached_word_pairs ADD COLUMN added_at TEXT` wrapped in a try/except for the "duplicate column" error. This is the simplest and safest approach.

## Notes / risks

- **Risk**: Existing SQLite files without `added_at` column will fail on insert with 7 values.
  - **Mitigation**: Add a schema migration step in `open()` that adds the column if missing. The `ALTER TABLE ... ADD COLUMN` is idempotent-safe (catch `OperationalError` for "duplicate column name").
- **Risk**: The `RemoteProgressSyncPort.export_remote_snapshot()` protocol return type says `list[WordPairSnapshot]` but runtime returns `list[EnrichedWordPairSnapshot]`. Type checkers may complain about accessing `.added_at`.
  - **Mitigation**: Use `hasattr(sp, 'added_at')` or cast. The runtime objects do have the attribute. A `# type: ignore[attr-defined]` comment is acceptable here with a clear explanation.
