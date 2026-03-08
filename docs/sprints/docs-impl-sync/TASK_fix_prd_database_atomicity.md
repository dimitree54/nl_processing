---
Task ID: T1
Title: Add atomicity and delta-validation language to FR38-40 in prd_database.md
Sprint: 2026-03-08_docs-impl-sync
Module: database (docs only)
Depends on: —
Parallelizable: yes, with T2, T3, T4
Owner: Developer
Status: planned
---

## Goal / value

After this task, `prd_database.md` FR38-40 accurately describe how `apply_score_delta` works in the implementation: the check-increment-mark operation is atomic (single database transaction), `delta` is validated to be `+1` or `-1`, and `exercise_type` is validated against the configured set.

## Context (contract mapping)

- PRD: `nl_processing/database/docs/prd_database.md` lines 225-227 (FR38-40)
- Architecture (already correct): `nl_processing/database/docs/architecture_database.md` lines 119-126
- Implementation: `nl_processing/database/exercise_progress.py` lines 113-137

## Preconditions

- None — this task can be executed independently.

## Non-goals

- Do NOT change the architecture doc (it already correctly describes atomicity).
- Do NOT reduce `prd_database.md` line count in this task (T5 handles that).
- Do NOT modify any `.py` files.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**

- `nl_processing/database/docs/prd_database.md`

**FORBIDDEN — this task must NEVER touch:**

- Any `.py` source or test file
- Any other doc file
- Any file outside the module's `docs/` directory

**Test scope:**

- Verification: `make check` must remain 100% green
- No new tests — this is a docs-only change

## Touched surface (expected files / modules)

- `nl_processing/database/docs/prd_database.md` (lines 225-227)

## Dependencies and sequencing notes

- No upstream dependencies.
- T5 (line-count reduction for `prd_database.md`) depends on this task completing first, because both tasks modify the same file.

## Third-party / library research

N/A — no external dependencies.

## Implementation steps (developer-facing)

1. Open `nl_processing/database/docs/prd_database.md`.

2. Locate FR38 (line 225). Current text:
   ```
   - FR38: Module exposes an internal `apply_score_delta(event_id, ...)` operation for cache replay.
   ```

3. Replace FR38 with:
   ```
   - FR38: Module exposes an internal `apply_score_delta(event_id, ...)` operation for cache replay. The check-increment-mark operation is atomic (single database transaction).
   ```

4. Locate FR39 (line 226). Keep it as-is — it correctly describes the idempotency key.

5. After FR40 (line 227), add a new FR41:
   ```
   - FR41: `apply_score_delta` validates `delta` is `+1` or `-1` and `exercise_type` belongs to the configured set before any database operation.
   ```

6. Verify `make check` still passes.

## Production safety constraints

N/A — documentation-only change. No database, code, or runtime impact.

## Anti-disaster constraints

- **Reuse before build**: modifying existing doc, not creating new files.
- **No regressions**: doc-only change; `make check` verifies no breakage.

## Error handling + correctness rules

N/A — documentation-only change.

## Zero legacy tolerance rule

After this task, FR38-40 fully match the implemented behavior. No legacy description of `apply_score_delta` as non-atomic remains in the PRD.

## Acceptance criteria (testable)

1. FR38 in `prd_database.md` explicitly states the check-increment-mark operation is atomic (single transaction).
2. A new FR41 exists stating that `apply_score_delta` validates `delta` and `exercise_type` before any database operation.
3. `make check` passes.
4. No `.py` files were modified.

## Verification / quality gates

- [ ] FR38 text updated to mention atomicity
- [ ] FR41 added for delta + exercise_type validation
- [ ] `make check` passes
- [ ] No files outside `nl_processing/database/docs/prd_database.md` were touched

## Edge cases

- The new FR41 number must not conflict with any existing FR numbering in the file (currently ends at FR40, so FR41 is safe).

## Notes / risks

- Low risk — additive text change to a documentation file.
