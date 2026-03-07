---
Task ID: `T5`
Title: `Sync database docs with implementation`
Sprint: `2026-03-07_database-cache-extraction`
Module: `database`
Depends on: `T1, T2, T3, T4`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Update `architecture_database.md` and `prd_database.md` so they accurately reflect the current codebase after T1-T4 changes. Fix discrepancies 1, 2, 3, and the removal of `CachedDatabaseService` from the module structure listing. After this task, every line of the `database` docs matches reality.

## Context (contract mapping)

- Sprint request: Discrepancy 1 -- "`DatabaseCacheSyncBackend` Protocol doesn't exist."
- Sprint request: Discrepancy 2 -- "`export_remote_snapshot` returns combined data vs docs' two-method design."
- Sprint request: Discrepancy 3 -- "Architecture doc omits `_neon_exercise.py` and `_queries.py`."
- Sprint request: Discrepancy 9 -- `cached_service.py` listed in module structure (now deleted).
- Current docs: `nl_processing/database/docs/architecture_database.md`, `nl_processing/database/docs/prd_database.md`

## Preconditions

- T1 completed (CachedDatabaseService deleted -- module structure must reflect this).
- T2 completed (delta validation added -- docs should reflect this behavior).
- T3 completed (atomic apply_score_delta -- architecture should describe the atomicity decision).
- T4 completed (FR21 warning logging implemented -- implementation considerations may note this).

## Non-goals

- Updating `database_cache` docs (that is T6).
- Updating `docs/planning-artifacts/architecture.md` (shared architecture, out of scope).
- Adding new requirements or architecture decisions -- this task only syncs existing docs to match existing code.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `nl_processing/database/docs/architecture_database.md`
- `nl_processing/database/docs/prd_database.md`

**FORBIDDEN -- this task must NEVER touch:**
- Any source code files
- Any test files
- `vulture_whitelist.py`
- `database_cache` docs (T6)
- `docs/planning-artifacts/`

**Test scope:**
- Verification command: `make check` (doc changes don't break any checks)

## Touched surface (expected files / modules)

- `nl_processing/database/docs/architecture_database.md` -- multiple sections updated
- `nl_processing/database/docs/prd_database.md` -- minor updates

## Dependencies and sequencing notes

- Depends on T1-T4 so that all code changes are finalized before docs are synced.
- T6 depends on this task (T6 syncs `database_cache` docs, which reference `database` API).

## Third-party / library research (mandatory for any external dependency)

N/A -- documentation task only.

## Implementation steps (developer-facing)

### Step 1: Update `architecture_database.md` Module Internal Structure (lines 122-140)

Replace the module structure block to match reality:

```
nl_processing/database/
├── __init__.py
├── service.py                   # DatabaseService
├── exercise_progress.py         # ExerciseProgressStore + cache-support helpers
├── backend/
│   ├── __init__.py
│   ├── abstract.py              # AbstractBackend ABC
│   ├── neon.py                  # NeonBackend (asyncpg)
│   ├── _neon_exercise.py        # Exercise-related backend operations
│   └── _queries.py              # SQL query templates
├── models.py                    # AddWordsResult, WordPair, ScoredWordPair
├── exceptions.py                # ConfigurationError, DatabaseError
├── logging.py                   # get_logger
├── testing.py                   # Test-only utilities (NOT production)
└── docs/
    ├── product-brief-database-2026-03-02.md
    ├── prd_database.md
    └── architecture_database.md
```

Key changes:
- **Remove** `cached_service.py` line.
- **Add** `_neon_exercise.py` and `_queries.py` under `backend/`.

### Step 2: Update `architecture_database.md` cache-support section (lines 93-104)

Replace the `DatabaseCacheSyncBackend` Protocol block. The current code exposes cache support through `ExerciseProgressStore` instance methods, not through a separate Protocol class. Update to reflect reality:

Replace:
```python
class DatabaseCacheSyncBackend(Protocol):
    async def export_user_word_pairs(...) -> list[RemoteWordPairRecord]: ...
    async def export_user_scores(...) -> list[RemoteScoreRecord]: ...
    async def apply_score_delta(event_id: str, ...) -> None: ...
```

With:
```python
# Cache support is provided through ExerciseProgressStore instance methods:
progress = ExerciseProgressStore(
    user_id="alex",
    source_language=Language.NL,
    target_language=Language.RU,
    exercise_types=["nl_to_ru", "multiple_choice"],
)

# Snapshot export (word pairs + scores for all configured exercises):
snapshot: list[ScoredWordPair] = await progress.export_remote_snapshot()

# Idempotent score delta replay (atomic, transactional):
await progress.apply_score_delta(
    event_id="uuid-here",
    source_word_id=101,
    exercise_type="nl_to_ru",
    delta=-1,
)
```

Update the surrounding prose:
- Remove references to `DatabaseCacheSyncBackend` Protocol.
- Remove references to `RemoteWordPairRecord` and `RemoteScoreRecord` types.
- Note that `export_remote_snapshot()` returns `list[ScoredWordPair]` which contains both word pairs and scores in a single call.
- Note that `apply_score_delta` is now atomic (wraps check-increment-mark in a single transaction).

### Step 3: Add atomicity decision to `architecture_database.md`

After the existing "Decision: Idempotent Score Replay" section (around line 108), add or update:

```markdown
### Decision: Atomic Score Replay

`apply_score_delta(event_id, ...)` wraps the event-check, score-increment, and event-mark operations in a single database transaction via `AbstractBackend.apply_score_delta_atomic(...)`.

**Rationale:** Without a transaction, a crash between increment and mark could cause a lost idempotency record or a double-apply on retry. The atomic method guarantees all-or-nothing semantics.
```

### Step 4: Update `prd_database.md` cache-support code example (lines 139-147)

The existing code example in the "Internal cache-support interface" section is correct and matches the implementation. Verify it matches and leave as-is. The snapshot/delta API shown is:
```python
snapshot = await progress.export_remote_snapshot()
await progress.apply_score_delta(
    event_id="...",
    source_word_id=101,
    exercise_type="nl_to_ru",
    delta=-1,
)
```
This is already correct.

### Step 5: Verify line counts

Both doc files must remain reasonable. `architecture_database.md` is currently 163 lines; after edits it should be approximately 170-180 lines. `prd_database.md` is 259 lines; it should remain approximately the same (the PRD is exempt from the 200-line pylint check since it is a .md file, not .py).

### Step 6: Run `make check`

Confirm 100% green. Doc-only changes should not affect any checks.

## Production safety constraints (mandatory)

- N/A -- documentation-only changes.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: N/A.
- **Correct libraries only**: N/A.
- **Correct file locations**: Only touching existing doc files in their current locations.
- **No regressions**: No code changes.

## Error handling + correctness rules (mandatory)

- N/A -- documentation-only task.

## Zero legacy tolerance rule (mandatory)

- Remove all references to `CachedDatabaseService` from architecture docs.
- Remove all references to `DatabaseCacheSyncBackend` Protocol.
- Remove all references to phantom types `RemoteWordPairRecord` and `RemoteScoreRecord`.

## Acceptance criteria (testable)

1. `architecture_database.md` module structure lists `_neon_exercise.py` and `_queries.py`.
2. `architecture_database.md` module structure does NOT list `cached_service.py`.
3. `architecture_database.md` does NOT mention `DatabaseCacheSyncBackend` Protocol.
4. `architecture_database.md` does NOT mention `RemoteWordPairRecord` or `RemoteScoreRecord`.
5. `architecture_database.md` cache-support section shows `ExerciseProgressStore` instance methods with correct signatures.
6. `architecture_database.md` documents the atomic score replay decision.
7. `prd_database.md` cache-support code example matches actual API.
8. `make check` is 100% green.

## Verification / quality gates

- [ ] Module structure in architecture doc matches actual file listing
- [ ] No phantom types or protocols referenced
- [ ] Cache-support section reflects actual `ExerciseProgressStore` API
- [ ] Atomicity decision documented
- [ ] `make check` passes
- [ ] No references to deleted `CachedDatabaseService` in database docs

## Edge cases

- None -- documentation-only task.

## Notes / risks

- **Risk**: None. Documentation changes cannot break tests or builds.
- The shared architecture (`docs/planning-artifacts/architecture.md`) still mentions `CachedDatabaseService` on lines 432-433. That is out of scope for this sprint (it's a shared document, not module-specific). A follow-up task or separate PR should address it.
