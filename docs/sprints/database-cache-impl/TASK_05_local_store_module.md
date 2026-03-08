---
Task ID: T5
Title: Create `local_store.py` — SQLite schema and CRUD operations
Sprint: 2026-03-08_database-cache-impl
Module: database_cache
Depends on: T1, T2, T3, T4
Parallelizable: no
Owner: Developer
Status: planned
---

## Goal / value

Create `local_store.py` — the SQLite data access layer that manages the 4 local tables (`cached_word_pairs`, `cached_scores`, `pending_score_events`, `cache_metadata`). This file handles schema creation, all local reads/writes, atomic snapshot rebuilds, and metadata operations. It is the foundation for the service and sync layers.

## Context (contract mapping)

- Architecture: `nl_processing/database_cache/docs/architecture_database_cache.md` — "Local Data Model" section defines all 4 tables with exact column types and keys
- Requirements:
  - FR4: `init()` opens or creates local cache → `LocalStore.open()`
  - FR8–FR9: `get_words()` → `LocalStore` read methods
  - FR10–FR11: `get_word_pairs_with_scores()` → `LocalStore` join read
  - FR13: Raise `CacheNotReadyError` if no snapshot → checked via metadata
  - FR14–FR18: `record_exercise_result()` → transactional score update + outbox insert
  - FR20: Refresh rebuilds snapshot atomically → staging tables + swap
  - FR22: Pending events reapplied after refresh → outbox query
  - FR27–FR28: Exercise types stored in metadata → metadata read/write
  - FR30: Status from metadata → metadata query

## Preconditions

- T1 complete (`aiosqlite` available)
- T2 complete (`exceptions.py` — `CacheNotReadyError`, `CacheStorageError`)
- T3 complete (`models.py` — `CacheStatus`)
- T4 complete (`logging.py`)

## Non-goals

- Orchestrating refresh/flush (that's `sync.py`, T6)
- Managing the `ExerciseProgressStore` dependency (that's `service.py`, T7)
- Writing tests (T9)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/database_cache/local_store.py` — create this file

**FORBIDDEN — this task must NEVER touch:**
- Any other module's code or tests
- `nl_processing/database/` (consumed, not modified)

**Test scope:**
- No tests to write for this task
- Verification: `make check` passes

## Touched surface (expected files / modules)

- `nl_processing/database_cache/local_store.py` (new file)

## Dependencies and sequencing notes

- Must wait for T2 (exceptions), T3 (models), T4 (logging)
- T6 (sync) and T7 (service) depend on this task
- Cannot be parallelized — it is on the critical path

## Third-party / library research (mandatory for any external dependency)

- **Library**: `aiosqlite` 0.20+
- **Documentation**: https://aiosqlite.omnilib.dev/en/stable/api.html
- **Key API patterns**:
  ```python
  import aiosqlite

  # Open connection
  db = await aiosqlite.connect("cache.db")
  db.row_factory = aiosqlite.Row  # dict-like row access

  # Execute with parameters
  await db.execute("INSERT INTO t (col) VALUES (?)", (value,))

  # Transaction (explicit)
  async with db.cursor() as cursor:
      await cursor.execute("INSERT ...")
      await cursor.execute("INSERT ...")
  await db.commit()

  # Query
  async with db.execute("SELECT * FROM t WHERE id=?", (1,)) as cursor:
      rows = await cursor.fetchall()

  # Close
  await db.close()
  ```
- **Known gotchas**:
  - `aiosqlite.Row` provides dict-like access via column names.
  - Must call `await db.commit()` explicitly — no autocommit.
  - `executescript()` available for DDL but does not support parameters.
  - WAL mode: `PRAGMA journal_mode=WAL` — recommended for concurrent read/write.

## Implementation steps (developer-facing)

1. Create `nl_processing/database_cache/local_store.py`.

2. Define a `LocalStore` class with the following responsibilities:

   **Constructor** — store the db path; do not open the connection yet.

   **`async open(db_path: str) -> None`** — open the SQLite file, enable WAL mode, create tables if they don't exist.

   **Schema DDL** — define and execute CREATE TABLE IF NOT EXISTS for:
   - `cached_word_pairs` (PK: `source_word_id`):
     - `source_word_id INTEGER PRIMARY KEY`
     - `source_normalized_form TEXT NOT NULL`
     - `source_word_type TEXT NOT NULL`
     - `target_word_id INTEGER NOT NULL`
     - `target_normalized_form TEXT NOT NULL`
     - `target_word_type TEXT NOT NULL`
   - `cached_scores` (PK: `source_word_id, exercise_type`):
     - `source_word_id INTEGER NOT NULL`
     - `exercise_type TEXT NOT NULL`
     - `score INTEGER NOT NULL DEFAULT 0`
     - `updated_at TEXT NOT NULL`
     - `PRIMARY KEY (source_word_id, exercise_type)`
   - `pending_score_events` (PK: `event_id`):
     - `event_id TEXT PRIMARY KEY`
     - `source_word_id INTEGER NOT NULL`
     - `exercise_type TEXT NOT NULL`
     - `delta INTEGER NOT NULL`
     - `created_at TEXT NOT NULL`
     - `flushed_at TEXT`
     - `last_error TEXT`
   - `cache_metadata` (single-row, PK: `id`):
     - `id INTEGER PRIMARY KEY DEFAULT 1`
     - `exercise_types TEXT NOT NULL` (JSON-encoded list)
     - `schema_version INTEGER NOT NULL DEFAULT 1`
     - `last_refresh_started_at TEXT`
     - `last_refresh_completed_at TEXT`
     - `last_flush_completed_at TEXT`
     - `last_error TEXT`

   **`async close() -> None`** — close the SQLite connection.

   **Read methods:**
   - `async get_cached_word_pairs(word_type: str | None, limit: int | None, random: bool) -> list[dict[str, ...]]` — query `cached_word_pairs`, optional filter by `source_word_type`, optional limit, optional random order (ORDER BY RANDOM()).
   - `async get_cached_word_pairs_with_scores(exercise_types: list[str]) -> list[dict[str, ...]]` — join `cached_word_pairs` with `cached_scores` for each exercise type; missing scores default to 0.
   - `async get_pending_events() -> list[dict[str, ...]]` — select unflushed events (where `flushed_at IS NULL`), ordered by `created_at`.
   - `async get_pending_event_count() -> int` — count of unflushed events.
   - `async get_metadata() -> dict[str, ...] | None` — read the single metadata row.
   - `async has_snapshot() -> bool` — True if `cached_word_pairs` has at least one row.

   **Write methods:**
   - `async record_score_and_event(source_word_id: int, exercise_type: str, delta: int, event_id: str) -> None` — in a single transaction: UPSERT `cached_scores` (increment score) + INSERT `pending_score_events`. This is the transactional outbox pattern (FR16).
   - `async rebuild_snapshot(word_pairs: list[...], scores: dict[...]) -> None` — atomically: DELETE all from `cached_word_pairs` and `cached_scores`, INSERT new data, then reapply pending events on top of new scores. Must be in a single transaction.
   - `async mark_event_flushed(event_id: str) -> None` — set `flushed_at` on a pending event.
   - `async mark_event_failed(event_id: str, error: str) -> None` — set `last_error` on a pending event.
   - `async update_metadata(**fields) -> None` — update metadata fields (e.g., `last_refresh_completed_at`, `exercise_types`).
   - `async ensure_metadata(exercise_types: list[str]) -> None` — INSERT OR REPLACE the metadata row with given exercise_types.

3. Use `aiosqlite.Row` as row factory for dict-like access.

4. All timestamps stored as ISO 8601 strings (`datetime.now(tz=UTC).isoformat()`).

5. Keep the file ≤ 200 lines. If it exceeds this, split table DDL into a module-level constant string and keep methods concise. The architecture already delegates sync orchestration to `sync.py`.

## Production safety constraints (mandatory)

- **Database operations**: Local SQLite only. Never touches Neon/remote databases.
- **Resource isolation**: SQLite file path is configurable. Tests will use `tmp_path` fixtures.
- **Migration preparation**: N/A — local cache schema, not production DB.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: No existing local store to reuse — greenfield implementation.
- **Correct libraries only**: `aiosqlite` (added in T1).
- **Correct file locations**: `nl_processing/database_cache/local_store.py` per architecture spec.
- **No regressions**: New file, no existing code affected.

## Error handling + correctness rules (mandatory)

- Wrap `aiosqlite` errors (e.g., `sqlite3.OperationalError`) in `CacheStorageError` with a descriptive message.
- Never swallow exceptions — if a transaction fails, let the error propagate after wrapping.
- `record_score_and_event()` must be atomic — either both the score update and outbox insert succeed, or neither does.

## Zero legacy tolerance rule (mandatory)

- No legacy code to remove — new file.

## Acceptance criteria (testable)

1. File `nl_processing/database_cache/local_store.py` exists.
2. `LocalStore` class is defined with `open()`, `close()`, and all read/write methods listed above.
3. Schema DDL creates all 4 tables with correct columns and primary keys.
4. `record_score_and_event()` performs score upsert + outbox insert in a single transaction.
5. `rebuild_snapshot()` atomically replaces word pairs and scores, then reapplies pending events.
6. All SQLite errors are wrapped in `CacheStorageError`.
7. File is ≤ 200 lines.
8. `make check` passes.

## Verification / quality gates

- [ ] File exists with correct content
- [ ] `make check` passes (ruff, pylint 200-line limit, vulture)
- [ ] No new warnings introduced

## Edge cases

- Empty database (first run) — `open()` must create all tables.
- `rebuild_snapshot()` called with no pending events — still works (no reapply needed).
- `rebuild_snapshot()` called with pending events — pending event deltas must be overlaid on new scores.
- `get_cached_word_pairs_with_scores()` when a word has no score row for an exercise type — must return 0.
- Concurrent calls — `aiosqlite` serializes via background thread, but caller (service/sync) must still guard against concurrent refresh/flush.

## Notes / risks

- **Risk**: File exceeds 200 lines due to 4 tables + many CRUD methods.
  - **Mitigation**: Keep methods concise. DDL can be a module-level constant. Sync orchestration is in `sync.py`. If still over 200 lines, extract DDL into a private constant or split read/write into separate helper functions.
