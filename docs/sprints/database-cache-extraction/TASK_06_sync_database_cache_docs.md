---
Task ID: `T6`
Title: `Sync database_cache docs with actual database API`
Sprint: `2026-03-07_database-cache-extraction`
Module: `database_cache` (docs only)
Depends on: `T5`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Update `architecture_database_cache.md` and `prd_database_cache.md` so their "Remote Integration Contract" section accurately describes the actual `database` API that `database_cache` will consume. Remove phantom types (`RemoteWordPairRecord`, `RemoteScoreRecord`) and the phantom `DatabaseCacheSyncBackend` Protocol. Replace with the real `ExerciseProgressStore` API. After this task, the `database_cache` docs are implementable against the real `database` module.

## Context (contract mapping)

- Sprint request: Discrepancy 1 -- "`DatabaseCacheSyncBackend` Protocol doesn't exist."
- Sprint request: Discrepancy 2 -- "`export_remote_snapshot` returns combined data vs docs' two-method design."
- Sprint request: Discrepancy 8 -- "`database_cache` docs assume APIs that don't exist in `database`."
- Current docs: `nl_processing/database_cache/docs/architecture_database_cache.md` lines 157-191, `nl_processing/database_cache/docs/prd_database_cache.md`.

## Preconditions

- T5 completed (database docs are synced first, so the `database_cache` docs can reference them accurately).
- The actual `database` API is:
  - `ExerciseProgressStore.export_remote_snapshot()` -> `list[ScoredWordPair]`
  - `ExerciseProgressStore.apply_score_delta(event_id, source_word_id, exercise_type, delta)` -> `None`
  - `ScoredWordPair` contains `pair: WordPair`, `scores: dict[str, int]`, `source_word_id: int`

## Non-goals

- Implementing `database_cache` module code (future sprint).
- Changing `database` module code.
- Changing `prd_database.md` or `architecture_database.md` (already done in T5).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `nl_processing/database_cache/docs/architecture_database_cache.md`
- `nl_processing/database_cache/docs/prd_database_cache.md` (if references to phantom types exist)

**FORBIDDEN -- this task must NEVER touch:**
- Any source code files
- Any test files
- `vulture_whitelist.py`
- `database` docs (already synced in T5)
- `docs/planning-artifacts/`

**Test scope:**
- Verification command: `make check` (doc changes don't break any checks)

## Touched surface (expected files / modules)

- `nl_processing/database_cache/docs/architecture_database_cache.md` -- Remote Integration Contract section rewritten
- `nl_processing/database_cache/docs/prd_database_cache.md` -- minor updates if needed

## Dependencies and sequencing notes

- Depends on T5 so that the `database` docs are accurate before syncing `database_cache` docs.
- This is the final task in the sprint.

## Third-party / library research (mandatory for any external dependency)

N/A -- documentation task only.

## Implementation steps (developer-facing)

### Step 1: Rewrite Remote Integration Contract in `architecture_database_cache.md` (lines 157-191)

Replace the current `DatabaseCacheSyncBackend` Protocol block:

**Current (REMOVE):**
```python
class DatabaseCacheSyncBackend(Protocol):
    async def export_user_word_pairs(
        self,
        user_id: str,
        source_language: Language,
        target_language: Language,
    ) -> list[RemoteWordPairRecord]:
        ...

    async def export_user_scores(
        self,
        user_id: str,
        source_language: Language,
        target_language: Language,
        exercise_types: list[str],
    ) -> list[RemoteScoreRecord]:
        ...

    async def apply_score_delta(
        self,
        event_id: str,
        user_id: str,
        source_language: Language,
        target_language: Language,
        source_word_id: int,
        exercise_type: str,
        delta: int,
    ) -> None:
        ...
```

**Replacement:**
```markdown
## Remote Integration Contract

`database_cache` consumes `ExerciseProgressStore` from the `database` module directly. No separate Protocol is needed because `ExerciseProgressStore` is already a well-defined class with stable instance methods for cache support.

### Snapshot Export

```python
from nl_processing.database.exercise_progress import ExerciseProgressStore
from nl_processing.database.models import ScoredWordPair

progress = ExerciseProgressStore(
    user_id="alex",
    source_language=Language.NL,
    target_language=Language.RU,
    exercise_types=["nl_to_ru", "multiple_choice"],
)

snapshot: list[ScoredWordPair] = await progress.export_remote_snapshot()
```

`export_remote_snapshot()` returns a list of `ScoredWordPair`, each containing:
- `pair: WordPair` with `source: Word` and `target: Word` (translated pair)
- `scores: dict[str, int]` (score per configured exercise type, missing defaults to 0)
- `source_word_id: int` (remote canonical ID for the source word)

This single call replaces the previously documented `export_user_word_pairs` and `export_user_scores` methods. Word pairs and scores are returned together because they share the same row context.

### Idempotent Score Delta Replay

```python
await progress.apply_score_delta(
    event_id="uuid-here",
    source_word_id=101,
    exercise_type="nl_to_ru",
    delta=-1,  # must be +1 or -1
)
```

- `event_id` is the idempotency key. Repeating the same `event_id` is a no-op.
- `delta` must be +1 or -1 (validated, raises `ValueError` otherwise).
- The check-increment-mark operation is atomic (single database transaction).
- `exercise_type` must belong to the store's configured exercise set.

### Design Decision: Direct Dependency, Not Protocol

`database_cache` depends directly on `ExerciseProgressStore` rather than an abstract Protocol because:
1. There is exactly one implementation of the remote sync contract.
2. The `ExerciseProgressStore` constructor already handles user/language/exercise-type scoping.
3. Test isolation is achieved by injecting a mock backend into the store, not by abstracting the store itself.
```

### Step 2: Update Lifecycle Flow references in `architecture_database_cache.md`

In the "Refresh" section (lines 203-209), update step 1:
- **Current**: "Fetch remote word pairs and scores for the configured exercise set."
- **Updated**: "Call `progress.export_remote_snapshot()` to fetch word pairs with scores for the configured exercise set."

In the "Flush" section (lines 219-223), update step 2:
- **Current**: "Replay each event remotely using `event_id`."
- **Updated**: "Replay each event by calling `progress.apply_score_delta(event_id=..., source_word_id=..., exercise_type=..., delta=...)`."

### Step 3: Check `prd_database_cache.md` for phantom type references

Search for `RemoteWordPairRecord`, `RemoteScoreRecord`, `DatabaseCacheSyncBackend`, `export_user_word_pairs`, `export_user_scores` in `prd_database_cache.md`.

The PRD does not use these specific type/method names. It describes behavior at a higher level:
- FR19: "refresh() fetches translated word pairs and scores" -- correct, no phantom types.
- FR23: "flush() replays pending events to remote database" -- correct.
- NFR11: "depends on database for snapshot export and idempotent remote replay" -- correct.

No changes needed in `prd_database_cache.md` unless phantom types are found upon re-reading.

### Step 4: Remove stale product brief references

Check `product-brief-database_cache-2026-03-07.md`:
- Line 50 mentions "Current in-memory `CachedDatabaseService`" -- this is a problem statement, not a dependency. It accurately describes WHY `database_cache` exists. Leave as-is (it's historical context).

### Step 5: Run `make check`

Confirm 100% green. Doc-only changes should not affect any checks.

## Production safety constraints (mandatory)

- N/A -- documentation-only changes.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: N/A.
- **Correct libraries only**: N/A.
- **Correct file locations**: Only touching existing doc files.
- **No regressions**: No code changes.

## Error handling + correctness rules (mandatory)

- N/A -- documentation-only task.

## Zero legacy tolerance rule (mandatory)

- Remove all references to `DatabaseCacheSyncBackend` Protocol from `database_cache` docs.
- Remove all references to phantom types `RemoteWordPairRecord` and `RemoteScoreRecord`.
- Remove all references to phantom methods `export_user_word_pairs` and `export_user_scores`.

## Acceptance criteria (testable)

1. `architecture_database_cache.md` does NOT mention `DatabaseCacheSyncBackend`.
2. `architecture_database_cache.md` does NOT mention `RemoteWordPairRecord` or `RemoteScoreRecord`.
3. `architecture_database_cache.md` does NOT mention `export_user_word_pairs` or `export_user_scores`.
4. `architecture_database_cache.md` Remote Integration Contract shows `ExerciseProgressStore.export_remote_snapshot()` and `ExerciseProgressStore.apply_score_delta(...)` with correct signatures.
5. `architecture_database_cache.md` documents that `apply_score_delta` validates delta and is atomic.
6. Lifecycle Flow references in `architecture_database_cache.md` use correct method names.
7. `prd_database_cache.md` contains no phantom type references.
8. `make check` is 100% green.

## Verification / quality gates

- [ ] No phantom Protocol, types, or methods in `database_cache` docs
- [ ] Remote Integration Contract matches actual `database` API
- [ ] Lifecycle Flow uses correct method names
- [ ] `make check` passes
- [ ] No references to deleted `CachedDatabaseService` as a dependency in `database_cache` architecture

## Edge cases

- None -- documentation-only task.

## Notes / risks

- **Risk**: None. Documentation changes cannot break tests or builds.
- **Note**: The `database_cache` product brief (line 50) mentions `CachedDatabaseService` in the "Why Existing Solutions Fall Short" section. This is acceptable historical context (it explains why the old approach was insufficient), not an API dependency. It does not need to be removed.
- **Note**: After this sprint, when someone implements the `database_cache` module, they will consume `ExerciseProgressStore` directly rather than implementing against a phantom Protocol. This is simpler, more explicit, and matches the actual `database` API.
