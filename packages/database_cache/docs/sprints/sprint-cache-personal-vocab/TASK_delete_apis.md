---
Task ID: `T5`
Title: `Implement delete_word() / delete_words() with remote-first + local prune`
Sprint: `2026-03-12_cache-personal-vocab`
Module: `database_cache`
Depends on: `T2`
Parallelizable: no (serialized after T4 due to file contention)
---

## Goal / value

`DatabaseCacheService.delete_word(source_word_id)` and `delete_words(source_word_ids)` call the remote delete API first, and only on success prune local SQLite rows (cached word pairs, cached scores, and pending score events) for the deleted IDs. This implements DEC-6 (remote-first, no delete outbox), FM-5 (remote failure surfaces error, local untouched), and BR-6 (successful delete also removes pending score events).

## Context (contract mapping)

- Requirements: `docs/module-spec.md` — FR-9, DEC-6, FM-5, BR-6, AC-6
- Module spec: `docs/module-spec.md` — IF-1, IF-2, QA-6
- Related: `database.service.DatabaseService.delete_word()` / `delete_words()` — remote implementation
- Related: `database.exceptions.WordNotFoundError` — raised by remote when word not found

## Preconditions

- T1 (decompose) is complete — `service.py` and `local_store.py` have headroom
- T2 (schema + refresh added_at) is complete — DDL is up to date

## Non-goals

- Building a delete outbox or offline delete capability (DEC-6 says no)
- Modifying `RemoteProgressSyncPort` in `core.ports` (forbidden)
- Modifying `DatabaseService` in `database` package (forbidden)

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

- `src/nl_processing/database_cache/service.py` — add `delete_word()`, `delete_words()` methods, new constructor param for remote delete dependency
- `src/nl_processing/database_cache/ports.py` — **new file**: `RemoteDeletePort` protocol
- `src/nl_processing/database_cache/local_store.py` — add `delete_cached_word()` method (deletes from `cached_word_pairs`, `cached_scores`, `pending_score_events` for a given `source_word_id`)
- `src/nl_processing/database_cache/_local_store_queries.py` — add delete SQL constants
- `tests/unit/database_cache/test_service.py` — add delete tests
- `tests/unit/database_cache/test_local_store.py` — add delete tests
- `tests/integration/database_cache/test_persistence.py` or new file — add delete persistence tests

## Dependencies and sequencing notes

- Depends on T2 for updated DDL (though delete operations work on any column set, the tests need the 7-element tuple format).
- Serialized after T4 because of file contention on `service.py`. In theory, could parallelize with T3/T4 after T2, but shared files make that risky.
- T6 (e2e) depends on this task.

## Third-party / library research (mandatory for any external dependency)

No new third-party libraries. Uses:
- `nl_processing.database.service.DatabaseService` — concrete class for remote deletes (default implementation).
- `nl_processing.database.exceptions.WordNotFoundError` — re-raised from remote delete failure.
- `typing.Protocol` (stdlib) — for the `RemoteDeletePort` protocol.

## Implementation steps (developer-facing)

### Step 1: Define `RemoteDeletePort` protocol

Create `src/nl_processing/database_cache/ports.py`:

```python
"""Port protocols for remote operations not covered by core.ports."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class RemoteDeletePort(Protocol):
    """Remote delete contract consumed by the cache for remote-first deletes."""

    async def delete_word(
        self, source_word_id: int, exercise_types: list[str] | None = None
    ) -> None: ...

    async def delete_words(
        self, source_word_ids: list[int], exercise_types: list[str] | None = None
    ) -> None: ...
```

This matches the signature of `DatabaseService.delete_word()` / `delete_words()`.

### Step 2: Add delete SQL constants to `_local_store_queries.py`

```python
DELETE_CACHED_WORD_PAIR = "DELETE FROM cached_word_pairs WHERE source_word_id = ?"
DELETE_CACHED_SCORES = "DELETE FROM cached_scores WHERE source_word_id = ?"
DELETE_PENDING_EVENTS = "DELETE FROM pending_score_events WHERE source_word_id = ? AND flushed_at IS NULL"
```

### Step 3: Add `delete_cached_word()` to `local_store.py`

```python
async def delete_cached_word(self, source_word_id: int) -> None:
    """Remove a word from cached_word_pairs, cached_scores, and pending_score_events."""
    try:
        await self._conn.execute(DELETE_CACHED_WORD_PAIR, (source_word_id,))
        await self._conn.execute(DELETE_CACHED_SCORES, (source_word_id,))
        await self._conn.execute(DELETE_PENDING_EVENTS, (source_word_id,))
        await self._conn.commit()
    except sqlite3.Error as exc:
        raise CacheStorageError(str(exc)) from exc
```

Add `DELETE_CACHED_WORD_PAIR`, `DELETE_CACHED_SCORES`, `DELETE_PENDING_EVENTS` to the imports from `_local_store_queries`.

### Step 4: Add remote delete dependency to `DatabaseCacheService.__init__()`

Add a new optional parameter `remote_db` to the constructor:

```python
def __init__(
    self,
    *,
    # ... existing params ...
    remote_db: RemoteDeletePort | None = None,  # NEW
) -> None:
    # ... existing init ...
    self._remote_db = remote_db
```

The default construction of `_remote_db` happens in `init()`, mirroring the existing pattern for `_remote_progress`:

```python
async def init(self) -> CacheStatus:
    # ... existing code ...
    if self._remote_db is None:
        from nl_processing.database.service import DatabaseService
        self._remote_db = DatabaseService(
            user_id=self._user_id,
            source_language=self._source_language,
            target_language=self._target_language,
        )
    # ... rest of init ...
```

Note: The lazy import avoids a top-level import of `DatabaseService` which would be a stronger coupling than needed. Tests inject a mock via the `remote_db` parameter.

### Step 5: Add `delete_word()` and `delete_words()` to `service.py`

```python
async def delete_word(self, source_word_id: int) -> None:
    """Delete a word: remote first, then prune local state (FR-9, DEC-6)."""
    self._ensure_ready()
    assert self._local is not None
    assert self._remote_db is not None
    await self._remote_db.delete_word(source_word_id, exercise_types=self._exercise_types)
    await self._local.delete_cached_word(source_word_id)

async def delete_words(self, source_word_ids: list[int]) -> None:
    """Delete multiple words: remote first, then prune local state (FR-9)."""
    self._ensure_ready()
    assert self._local is not None
    assert self._remote_db is not None
    await self._remote_db.delete_words(source_word_ids, exercise_types=self._exercise_types)
    for wid in source_word_ids:
        await self._local.delete_cached_word(wid)
```

**Key design decisions**:
- Remote delete is called first. If it raises, the exception propagates and local state is untouched (FM-5).
- `delete_words()` calls remote `delete_words()` atomically, then prunes locally one by one. If remote succeeds but local fails (SQLite error), that's a `CacheStorageError` — acceptable because the cache can be rebuilt via `refresh()`.
- `WordNotFoundError` from remote propagates to the caller unmodified.

### Step 6: Add unit tests

In `tests/unit/database_cache/test_service.py`:

1. **`test_delete_word_removes_from_local_cache`** — set up cache with 2 words, delete one, verify `get_words()` returns only 1 word.

2. **`test_delete_word_removes_scores`** — record a score for a word, delete it, verify scores for that word are gone.

3. **`test_delete_word_removes_pending_events`** — record exercise result (creates pending event), delete the word, verify pending events for that word are gone (BR-6).

4. **`test_delete_word_remote_failure_leaves_local_untouched`** — configure mock remote to raise `ConnectionError` on delete, verify local cache still has the word (FM-5).

5. **`test_delete_word_not_found_raises`** — configure mock remote to raise `WordNotFoundError`, verify it propagates.

6. **`test_delete_words_batch`** — delete 2 words in batch, verify both removed from local cache.

7. **`test_delete_word_before_init_raises`** — verify `CacheNotReadyError`.

In `tests/unit/database_cache/test_local_store.py`:

8. **`test_delete_cached_word_removes_all_related_data`** — insert pairs and scores, delete one word, verify the pair, scores, and any pending events for that word are gone while other words' data remains.

In `tests/unit/database_cache/conftest.py`:

9. Update `MockProgressStore` to add delete methods (or create a `MockRemoteDelete` class implementing `RemoteDeletePort`).

### Step 7: Add integration tests

In `tests/integration/database_cache/` — add a new file `test_delete.py` or add to `test_persistence.py`:

1. **`test_delete_persists_across_close_reopen`** — delete a word, close and reopen SQLite, verify the word is still deleted.

2. **`test_delete_and_refresh_does_not_bring_word_back`** — delete a word (from remote mock), update mock to not include the deleted word, refresh, verify the word is still gone.

### Step 8: Run tests and verify line counts

1. `uv run pytest tests/unit/database_cache/ -x -v`
2. `uv run pytest tests/integration/database_cache/ -x -v`
3. Verify all files under 200 lines:
   - `service.py`: added ~15 lines (init change + 2 methods)
   - `local_store.py`: added ~10 lines (1 method)
   - `_local_store_queries.py`: added ~3 lines (SQL constants)
   - `ports.py`: ~15 lines (new file)

## Production safety constraints (mandatory)

- **Database operations**: All remote delete calls go through a mock in tests. Never connect to the production database.
- **Local operations**: SQLite uses in-memory or `tmp_path` files in tests.
- **Remote-first guarantee**: The code structure ensures remote delete completes before local prune begins. If remote fails, local state is untouched.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Uses existing `DatabaseService.delete_word()` / `delete_words()` from the `database` package for the remote implementation (not reimplemented).
- **Correct libraries only**: No new dependencies. `typing.Protocol` is stdlib.
- **No regressions**: Existing tests must pass. Delete operations don't affect other functionality.

## Error handling + correctness rules (mandatory)

- **Do not silence errors**: Remote delete errors propagate directly to the caller. `WordNotFoundError` from remote is not caught or wrapped.
- **FM-5 strict compliance**: If remote delete raises, the method raises the same exception. No fallback. No local-only delete.
- **CacheStorageError**: If local delete fails after remote success, `CacheStorageError` is raised. The caller knows local state may be inconsistent, but a `refresh()` will fix it.
- **No empty catch blocks**: Every exception path is explicit.

## Zero legacy tolerance rule (mandatory)

After implementing this task:

- `delete_word()` and `delete_words()` are the canonical cache delete APIs.
- No alternative delete code paths exist in the module.
- The `RemoteDeletePort` protocol is the single injection point for remote delete behavior.

## Acceptance criteria (testable)

1. `DatabaseCacheService.delete_word(source_word_id)` exists and deletes from remote then local.
2. `DatabaseCacheService.delete_words(source_word_ids)` exists and deletes from remote then local.
3. After successful delete, `get_words()` no longer returns the deleted word.
4. After successful delete, `get_word_pairs_with_scores()` no longer returns the deleted word.
5. After successful delete, pending score events for the deleted word are removed (BR-6).
6. If remote delete raises, local state is untouched (FM-5).
7. `WordNotFoundError` from remote propagates to the caller.
8. Calling before `init()` raises `CacheNotReadyError`.
9. `RemoteDeletePort` protocol exists and `DatabaseService` satisfies it.
10. Integration test: delete persists across SQLite close/reopen.
11. All files remain under 200 lines.

## Verification / quality gates

- [ ] Unit tests added and pass: `uv run pytest tests/unit/database_cache/ -x -v`
- [ ] Integration tests added and pass: `uv run pytest tests/integration/database_cache/ -x -v`
- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] Negative-path tests: remote failure leaves local untouched; WordNotFoundError propagates; before-init raises CacheNotReadyError
- [ ] BR-6 verification: pending events are deleted alongside word data
- [ ] Line counts verified: all files under 200

## Edge cases

- Delete a word that doesn't exist locally but exists remotely — remote delete succeeds, local delete is a no-op (SQL `DELETE WHERE` on non-existent ID affects 0 rows, no error).
- Delete a word that exists locally but not remotely — remote raises `WordNotFoundError`, local untouched. Caller must handle.
- Delete a word with pending score events — pending events are deleted (BR-6). If flush runs concurrently, the event may already be flushed (has `flushed_at` set), but the `DELETE_PENDING_EVENTS` SQL only targets unflushed events (`flushed_at IS NULL`). Flushed events remain as audit trail. **Decision**: Delete ALL pending events for the word (including flushed ones) — they're irrelevant after the word is deleted. Update `DELETE_PENDING_EVENTS` to not filter by `flushed_at`.
- `delete_words([])` with empty list — remote `delete_words([])` is a no-op per `DatabaseService` implementation (loops over empty list). Local loop is empty. No error.
- Concurrent delete and refresh — if refresh runs after delete, the deleted word won't be in the remote snapshot (because it was deleted remotely first), so it won't reappear locally.

## Notes / risks

- **Risk**: The lazy import `from nl_processing.database.service import DatabaseService` in `init()` could fail if the `database` package is not installed.
  - **Mitigation**: The `database` package is already a declared dependency (the cache imports `ExerciseProgressStore` at the top level). The lazy import is only for organizational clarity.
- **Risk**: `delete_words()` calls `remote_db.delete_words()` then loops locally. If the remote deletes partially (some succeed, some fail) and raises, the local prune doesn't happen for any of them.
  - **Mitigation**: `DatabaseService.delete_words()` iterates internally and raises `WordNotFoundError` on the first missing word. This is the remote's behavior, not the cache's. The cache correctly propagates the error and leaves local state untouched. The caller can retry with corrected IDs.
- **Risk**: Adding the `remote_db` constructor parameter could confuse existing callers.
  - **Mitigation**: It's optional with `None` default and constructed lazily in `init()`. No existing callers need to change.
