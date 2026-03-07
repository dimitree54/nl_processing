---
Task ID: `T2`
Title: `Update SQL query templates for per-exercise-type tables and applied_events`
Sprint: `2026-03-07_database-exercise-tables`
Module: `database`
Depends on: `T1`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Update `_queries.py` to generate per-exercise-type table DDL (e.g., `user_word_exercise_scores_nl_ru_flashcard`) instead of the single shared table, and add DDL + queries for the `applied_events` idempotency-tracking table. Update score increment/get queries to target per-exercise-type tables (no `exercise_type` column needed — it's implicit in the table name).

## Context (contract mapping)

- Requirements: Sprint request item 1 — "Exercise Progress Tables: Single -> Per-Exercise-Type"
- Requirements: Sprint request item 3 — "Cache Support APIs" (needs `applied_events` table)
- Current: `_queries.py` (149 lines) has `create_exercise_scores_table(src, tgt)` creating `user_word_exercise_scores_{src}_{tgt}` with an `exercise_type` column.
- New: Table naming becomes `user_word_exercise_scores_{src}_{tgt}_{exercise_slug}`. Each table stores only one exercise type, so the `exercise_type` column is removed from the table schema and from score queries.

## Preconditions

- T1 completed (bug fix in place, `make check` green on unit tests).

## Non-goals

- Implementing the backend methods that call these queries (T3/T4).
- Implementing the `ExerciseProgressStore` refactor (T5).
- Touching any file outside `_queries.py`.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/database/backend/_queries.py` — SQL query templates

**FORBIDDEN — this task must NEVER touch:**
- `nl_processing/database/backend/abstract.py`
- `nl_processing/database/backend/neon.py`
- Any test files (queries are tested indirectly through backend tests in later tasks)
- Any other module's code

**Test scope:**
- No tests to run for this task in isolation (pure SQL string templates). Verified via linter + line count.
- Sanity check: `uv run ruff check nl_processing/database/backend/_queries.py`

## Touched surface (expected files / modules)

- `nl_processing/database/backend/_queries.py`

## Dependencies and sequencing notes

- Depends on T1 (must be green before proceeding).
- T3 (AbstractBackend) and T4 (NeonBackend) depend on these query functions existing.
- Cannot run in parallel with T3/T4 because those tasks import from this file.

## Implementation steps (developer-facing)

1. **Rename and update `create_exercise_scores_table`**:
   - Change signature from `create_exercise_scores_table(src, tgt)` to `create_exercise_scores_table(src, tgt, exercise_slug)`.
   - Table name becomes `user_word_exercise_scores_{src}_{tgt}_{exercise_slug}`.
   - Remove `exercise_type VARCHAR NOT NULL` column from schema.
   - Remove `exercise_type` from the UNIQUE constraint. New UNIQUE is `(user_id, source_word_id)`.
   - Keep `score`, `updated_at`, `user_id`, `source_word_id` columns.

2. **Update `increment_score_query`**:
   - The `table` parameter will now be the full suffix `{src}_{tgt}_{exercise_slug}`.
   - Remove `exercise_type` from INSERT columns and VALUES.
   - Remove `$3` (exercise_type) parameter. Renumber: `$1`=user_id, `$2`=source_word_id, `$3`=delta.
   - ON CONFLICT target becomes `(user_id, source_word_id)` (no exercise_type — table is per-type).
   - Update SET clause to use `$3` for delta.

3. **Update `get_scores_query`**:
   - Remove `exercise_type` from SELECT and WHERE.
   - Remove `AND exercise_type = ANY($3)`.
   - Only filter by `user_id = $1 AND source_word_id = ANY($2)`.
   - SELECT only `source_word_id, score`.

4. **Add `create_applied_events_table` function**:
   ```python
   def create_applied_events_table(src: str, tgt: str) -> str:
       return f"""
           CREATE TABLE IF NOT EXISTS applied_events_{src}_{tgt} (
               event_id VARCHAR PRIMARY KEY,
               applied_at TIMESTAMP NOT NULL DEFAULT NOW()
           )
       """
   ```

5. **Add `check_event_applied_query` function**:
   ```python
   CHECK_EVENT_APPLIED = """
       SELECT 1 FROM applied_events_{table}
       WHERE event_id = $1
   """
   ```
   — Make this a function taking `table` parameter.

6. **Add `mark_event_applied_query` function**:
   ```python
   def mark_event_applied_query(table: str) -> str:
       return f"""
           INSERT INTO applied_events_{table} (event_id)
           VALUES ($1)
           ON CONFLICT DO NOTHING
       """
   ```

7. **Line count check**: Current file is 149 lines. Changes: modified 3 functions, added 3 functions. Estimate ~160–175 lines. If over 200, split exercise-specific queries into `nl_processing/database/backend/_exercise_queries.py`.

8. **Linter check**:
   ```
   uv run ruff format nl_processing/database/backend/_queries.py
   uv run ruff check nl_processing/database/backend/_queries.py
   ```

## Production safety constraints (mandatory)

- **Database operations**: No DB connections in this task. Pure string template functions.
- **Resource isolation**: N/A — no external resources.
- **Migration preparation**: The DDL changes here are the basis for `MIGRATION_PLAN.md` (written separately).

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Extends existing query template pattern.
- **Correct file locations**: Same file, same module path.
- **No regressions**: Old function signatures are changed (not left as dead code). Callers (NeonBackend) will be updated in T4.

## Error handling + correctness rules (mandatory)

- No error handling in query templates (they return strings).
- SQL correctness verified by integration tests in T10.

## Zero legacy tolerance rule (mandatory)

- The old `create_exercise_scores_table(src, tgt)` (2-param version) is fully replaced — no dual-path.
- The old `increment_score_query` with `exercise_type` column is fully replaced.
- The old `get_scores_query` with `exercise_type` filter is fully replaced.

## Acceptance criteria (testable)

1. `create_exercise_scores_table("nl", "ru", "flashcard")` returns DDL for table `user_word_exercise_scores_nl_ru_flashcard` without an `exercise_type` column.
2. `increment_score_query("nl_ru_flashcard")` returns an INSERT/UPSERT using only `(user_id, source_word_id)` for conflict, with 3 parameters (user_id, source_word_id, delta).
3. `get_scores_query("nl_ru_flashcard")` returns a SELECT with only `source_word_id, score`, filtering by `user_id = $1 AND source_word_id = ANY($2)`.
4. `create_applied_events_table("nl", "ru")` returns DDL for `applied_events_nl_ru`.
5. `check_event_applied_query("nl_ru")` and `mark_event_applied_query("nl_ru")` return correct SQL.
6. `uv run ruff check nl_processing/database/backend/_queries.py` — no errors.
7. File is ≤ 200 lines.

## Verification / quality gates

- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] File ≤ 200 lines

## Edge cases

- Exercise slug with underscores (e.g., `listen_and_type`): table name becomes `user_word_exercise_scores_nl_ru_listen_and_type` — valid PostgreSQL identifier. No special handling needed.
- Empty exercise_slug: not a valid input — validation is in `ExerciseProgressStore` (T5), not here.

## Notes / risks

- **Risk**: Old callers of `create_exercise_scores_table(src, tgt)` (2 params) will break until T4 updates `NeonBackend`. This is expected — tasks are sequential.
- **Risk**: Line count. Estimate ~165 lines after changes. Monitor and split if needed.
