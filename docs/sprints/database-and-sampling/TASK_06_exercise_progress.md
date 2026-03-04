---
Task ID: `T6`
Title: `Implement ExerciseProgressStore`
Sprint: `2026-03-04_database-and-sampling`
Module: `database`
Depends on: `T5`
Parallelizable: `yes, with T7 and T8`
Owner: `Developer`
Status: `planned`
---

## Goal / value

`ExerciseProgressStore` provides per-user, per-exercise score tracking and score-aware word pair retrieval. This is the internal API consumed by the `sampling` module to determine which words to practice.

## Context (contract mapping)

- Requirements: `nl_processing/database/docs/prd_database.md` — FR28-FR35 (exercise progress tracking)
- Architecture: `nl_processing/database/docs/architecture_database.md` — Decision: Per-User Exercise Progress Tables, exercise_progress.py

## Preconditions

- T5 complete (DatabaseService exists, NeonBackend fully functional)
- T2 complete (models — ScoredWordPair, WordPair)

## Non-goals

- No sampling logic (that's T12)
- No unit tests (that's T9)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**

- `nl_processing/database/exercise_progress.py` — create

**FORBIDDEN — this task must NEVER touch:**

- `nl_processing/database/service.py` (already complete)
- `nl_processing/database/__init__.py` (must stay empty)
- Any other module's code or tests

**Test scope:**

- No new tests in this task (unit tests in T9, integration in T10)
- `make check` must pass

## Touched surface (expected files / modules)

- `nl_processing/database/exercise_progress.py` (new)

## Dependencies and sequencing notes

- Depends on T5 (needs NeonBackend pattern for database access)
- T9 (unit tests) and T12 (sampling) depend on this
- Can run in parallel with T7 and T8

## Third-party / library research (mandatory for any external dependency)

- No new third-party dependencies — uses asyncpg via NeonBackend, models from T2.

## Implementation steps (developer-facing)

1. **Create `nl_processing/database/exercise_progress.py`:**

2. **Implement `ExerciseProgressStore` class:**

   ```python
   class ExerciseProgressStore:
       def __init__(self, *, user_id: str,
                    source_language: Language,
                    target_language: Language) -> None:
   ```

   - Constructor: reads `os.environ["DATABASE_URL"]`, wraps `KeyError` in `ConfigurationError`
   - Creates `NeonBackend(database_url)` internally
   - Derives table names from languages: `user_word_exercise_scores_{src}_{tgt}`, `words_{src}`, `words_{tgt}`, `translations_{src}_{tgt}`

3. **Implement `increment(self, source_word: Word, exercise_type: str, delta: int) -> None`:**
   - Validate `delta` is +1 or -1 — raise `ValueError` with descriptive message otherwise
   - Look up `source_word` in the source language table by `normalized_form` to get its `id`
   - If word not found, raise `DatabaseError` (can't increment score for unknown word)
   - Call `backend.increment_user_exercise_score(table, user_id, word_id, exercise_type, delta)`

4. **Implement `get_word_pairs_with_scores(self, exercise_types: list[str]) -> list[ScoredWordPair]`:**
   - Get all user's translated word pairs (source word + target word) — similar query to `DatabaseService.get_words()` but without filters
   - For all source word IDs, query exercise scores via `backend.get_user_exercise_scores(table, user_id, source_word_ids, exercise_types)`
   - Build `ScoredWordPair` for each pair: `pair=WordPair(source=..., target=...)`, `scores={exercise_type: int_score}`
   - Missing scores default to 0 (per FR33)
   - Return `list[ScoredWordPair]`

5. **Word reconstruction**: When reading word rows from the database, reconstruct `Word` objects:
   - `normalized_form` from DB column
   - `word_type` from DB column → `PartOfSpeech(value)` enum conversion
   - `language` set programmatically based on which table was queried

6. **200-line awareness**: Two public methods + constructor + helpers. Should be well within 200 lines.

7. Run `make check`.

## Production safety constraints (mandatory)

- **Database operations**: No connections unless code is executed. Score table only accessed in dev via Doppler.
- **Resource isolation**: `DATABASE_URL` from Doppler dev environment.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Uses same `NeonBackend` as `DatabaseService` — no new backend code.
- **Correct file locations**: `exercise_progress.py` per architecture doc.
- **No regressions**: New file only.

## Error handling + correctness rules (mandatory)

- `ValueError` for invalid delta (not +1 or -1) — descriptive message.
- `DatabaseError` if source word not found in DB.
- `ConfigurationError` if `DATABASE_URL` missing.
- No silent fallbacks — missing scores default to 0 only for reads (per spec), not for writes.

## Zero legacy tolerance rule (mandatory)

- No old code paths affected.

## Acceptance criteria (testable)

1. `nl_processing/database/exercise_progress.py` defines `ExerciseProgressStore` class.
2. Constructor accepts `user_id`, `source_language`, `target_language`.
3. `increment(source_word, exercise_type, delta)` validates delta is +1/-1.
4. `increment` raises `ValueError` for delta != +1/-1.
5. `get_word_pairs_with_scores(exercise_types)` returns `list[ScoredWordPair]`.
6. Missing scores default to 0.
7. All public methods are `async def`.
8. File under 200 lines.
9. `make check` passes.

## Verification / quality gates

- [ ] ExerciseProgressStore implemented
- [ ] Delta validation with ValueError
- [ ] Missing scores default to 0
- [ ] File under 200 lines
- [ ] `make check` passes

## Edge cases

- `delta = 0` — must raise `ValueError` (only +1/-1 allowed)
- `delta = 2` — must raise `ValueError`
- `exercise_types = []` — return `ScoredWordPair` items with empty `scores` dict
- User has no words — return empty list
- Word exists in source table but has no translation — exclude from results (consistent with DatabaseService.get_words behavior)

## Notes / risks

- **Risk**: Shared backend instance between DatabaseService and ExerciseProgressStore.
  - **Mitigation**: Each creates its own backend instance (lazy connection). This is acceptable for v1 — connection pooling optimization can come later.
