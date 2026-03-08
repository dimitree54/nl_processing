---
Task ID: T7
Title: Create `service.py` — `DatabaseCacheService` main class
Sprint: 2026-03-08_database-cache-impl
Module: database_cache
Depends on: T5, T6
Parallelizable: no
Owner: Developer
Status: planned
---

## Goal / value

Create `service.py` with the `DatabaseCacheService` class — the public API of the `database_cache` module. This class ties together the local store, sync layer, and exercise progress store, exposing the clean interface specified in the PRD: `init()`, `get_words()`, `get_word_pairs_with_scores()`, `record_exercise_result()`, `refresh()`, `flush()`, `get_status()`.

## Context (contract mapping)

- Requirements: `nl_processing/database_cache/docs/prd_database_cache.md` — FR1–FR32, NFR1–NFR3
- Architecture: `nl_processing/database_cache/docs/architecture_database_cache.md` — "Module Internal Structure" (`service.py` = `DatabaseCacheService`), "Lifecycle Flow", "Remote Integration Contract"
- PRD API surface:
  ```python
  cache = DatabaseCacheService(
      user_id="alex",
      source_language=Language.NL,
      target_language=Language.RU,
      exercise_types=["nl_to_ru", "multiple_choice"],
      cache_ttl=timedelta(minutes=30),
  )
  status = await cache.init()
  pairs = await cache.get_words(word_type=PartOfSpeech.NOUN, limit=10, random=True)
  scored = await cache.get_word_pairs_with_scores()
  await cache.record_exercise_result(source_word, exercise_type, delta)
  await cache.flush()
  await cache.refresh()
  status = await cache.get_status()
  ```

## Preconditions

- T5 complete (`local_store.py` — `LocalStore`)
- T6 complete (`sync.py` — `CacheSyncer`)

## Non-goals

- Implementing SQLite CRUD (done in T5)
- Implementing refresh/flush orchestration (done in T6)
- Writing tests (T9)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/database_cache/service.py` — create this file

**FORBIDDEN — this task must NEVER touch:**
- `nl_processing/database/` — consumed, not modified
- Any other module's code or tests

**Test scope:**
- No tests to write for this task
- Verification: `make check` passes

## Touched surface (expected files / modules)

- `nl_processing/database_cache/service.py` (new file)

## Dependencies and sequencing notes

- Depends on T5 (local_store) and T6 (sync) — uses both
- T8 (init) depends on this
- On the critical path

## Third-party / library research (mandatory for any external dependency)

- **`datetime.timedelta`**: https://docs.python.org/3.12/library/datetime.html#timedelta-objects — used for `cache_ttl` parameter.
- **`asyncio.create_task()`**: https://docs.python.org/3.12/library/asyncio-task.html#asyncio.create_task — used for background refresh (FR6: stale snapshot triggers background refresh without blocking).
- **`uuid.uuid4()`**: https://docs.python.org/3.12/library/uuid.html#uuid.uuid4 — used to generate unique `event_id` for outbox events (FR18).
- **`ExerciseProgressStore`**: `nl_processing/database/exercise_progress.py` — constructor requires `user_id`, `source_language`, `target_language`, `exercise_types`.

## Implementation steps (developer-facing)

1. Create `nl_processing/database_cache/service.py`.

2. Define `DatabaseCacheService` class:

   **Constructor** `__init__(self, *, user_id, source_language, target_language, exercise_types, cache_ttl, cache_dir=None)`:
   - Validate `exercise_types` is non-empty (FR3): raise `ValueError` if empty.
   - Store all params as instance attributes.
   - Construct the SQLite file path: `{cache_dir or tempfile.gettempdir()}/{user_id}_{source_lang}_{target_lang}.db`.
   - Do NOT create `LocalStore`, `CacheSyncer`, or `ExerciseProgressStore` yet — defer to `init()`.
   - Set `self._initialized = False`.

   **`async init(self) -> CacheStatus`** (FR4–FR7):
   - Create `ExerciseProgressStore` with the constructor params.
   - Create `LocalStore` and call `await local_store.open(db_path)`.
   - Create `CacheSyncer(local_store, progress_store)`.
   - Read metadata. If exercise types changed (FR28), trigger rebuild.
   - Ensure metadata row exists with current exercise_types.
   - Check staleness: compare `last_refresh_completed_at` with `cache_ttl`.
   - If no snapshot exists (FR7): start bootstrap refresh (await it), mark as not ready until complete.
   - If snapshot exists but stale (FR6): fire background refresh via `asyncio.create_task()`.
   - If snapshot exists and fresh: no action.
   - Set `self._initialized = True`.
   - Return `CacheStatus` from current state.

   **`async get_words(self, *, word_type=None, limit=None, random=False) -> list[WordPair]`** (FR8–FR9, FR12–FR13):
   - If not initialized or no snapshot: raise `CacheNotReadyError` (FR13).
   - Delegate to `LocalStore.get_cached_word_pairs()`.
   - Transform rows to `WordPair` objects (using `Word` from `core.models`).
   - Return list.

   **`async get_word_pairs_with_scores(self) -> list[ScoredWordPair]`** (FR10–FR11, FR12–FR13):
   - If not initialized or no snapshot: raise `CacheNotReadyError`.
   - Delegate to `LocalStore.get_cached_word_pairs_with_scores()`.
   - Transform rows to `ScoredWordPair` objects.
   - Return list.

   **`async record_exercise_result(self, *, source_word, exercise_type, delta) -> None`** (FR14–FR18):
   - Validate `exercise_type` is in configured set (FR14): raise `ValueError` if not.
   - Validate `delta` is +1 or -1 (FR15): raise `ValueError` if not.
   - Look up `source_word_id` from local cache by matching `source_word.normalized_form` and `source_word.word_type`.
   - Generate `event_id = str(uuid4())` (FR18).
   - Call `LocalStore.record_score_and_event(source_word_id, exercise_type, delta, event_id)` (FR16).

   **`async refresh(self) -> None`** (FR19–FR22, FR25):
   - Delegate to `CacheSyncer.refresh()`.

   **`async flush(self) -> None`** (FR23–FR24, FR26):
   - Delegate to `CacheSyncer.flush()`.

   **`async get_status(self) -> CacheStatus`** (FR30–FR32):
   - Read metadata and pending event count from `LocalStore`.
   - Build and return `CacheStatus`.

3. Row-to-model transformation helper methods:
   - `_row_to_word_pair(row) -> WordPair` — construct `Word` objects from row columns, then `WordPair`.
   - `_row_to_scored_pair(row, scores) -> ScoredWordPair` — same, plus scores dict.

4. Keep file ≤ 200 lines. The heavy lifting is in `LocalStore` and `CacheSyncer`.

## Production safety constraints (mandatory)

- **Database operations**: Local SQLite + remote `ExerciseProgressStore`. Remote uses whatever `DATABASE_URL` is set. In tests, the progress store is mocked (unit/integration) or uses dev DB (E2E).
- **Resource isolation**: SQLite path includes user_id + language pair — no collision with production. Tests use `tmp_path`.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Delegates to `LocalStore` (T5) and `CacheSyncer` (T6) — no duplication.
- **Correct libraries only**: All stdlib or project-internal.
- **Correct file locations**: `nl_processing/database_cache/service.py` per architecture spec.
- **No regressions**: New file.

## Error handling + correctness rules (mandatory)

- `CacheNotReadyError` raised for reads before first snapshot (FR13).
- `ValueError` raised for invalid `exercise_type` or `delta` (FR14, FR15).
- Background refresh errors are caught and logged — they don't crash the caller (FR31).
- Never swallow errors — all exceptions either propagate or are logged + stored in metadata.

## Zero legacy tolerance rule (mandatory)

- No legacy code to remove.

## Acceptance criteria (testable)

1. File `nl_processing/database_cache/service.py` exists.
2. `DatabaseCacheService` constructor accepts `user_id`, `source_language`, `target_language`, `exercise_types`, `cache_ttl`, optional `cache_dir`.
3. `exercise_types` validated as non-empty (raises `ValueError`).
4. `init()` opens local store, checks staleness, triggers background refresh if stale, awaits bootstrap if no snapshot. Returns `CacheStatus`.
5. `get_words()` returns `list[WordPair]` from local cache. Raises `CacheNotReadyError` if no snapshot.
6. `get_word_pairs_with_scores()` returns `list[ScoredWordPair]` from local cache. Raises `CacheNotReadyError` if no snapshot.
7. `record_exercise_result()` validates inputs, generates `event_id`, delegates to `LocalStore.record_score_and_event()`.
8. `refresh()` delegates to `CacheSyncer.refresh()`.
9. `flush()` delegates to `CacheSyncer.flush()`.
10. `get_status()` returns `CacheStatus` from current metadata.
11. File is ≤ 200 lines.
12. `make check` passes.

## Verification / quality gates

- [ ] File exists with correct content
- [ ] `make check` passes
- [ ] No new warnings introduced

## Edge cases

- `init()` called twice — should be idempotent (reuse existing store/syncer).
- `record_exercise_result()` for a source_word not in cache — should raise a clear error.
- `get_words()` with no matching word_type — return empty list.
- Background refresh task exception — must be caught and logged, not crash the event loop.

## Notes / risks

- **Risk**: Background refresh task's exception might be silently lost if not handled.
  - **Mitigation**: Wrap the background task in a try/except that logs errors and updates metadata. Use a task callback or explicit error handling wrapper.
- **Risk**: `source_word_id` lookup in `record_exercise_result()` requires querying local cache by `normalized_form` + `word_type`.
  - **Mitigation**: `LocalStore` must support this lookup. If not in T5's initial API, add a query method. The developer should add a `get_source_word_id()` method to `LocalStore` during this task if needed.
