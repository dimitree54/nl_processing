---
Task ID: T2
Title: Reduce architecture_database_cache.md to ≤200 lines and clarify sampling claim
Sprint: 2026-03-08_docs-impl-sync
Module: database_cache (docs only)
Depends on: —
Parallelizable: yes, with T1, T3, T4, T5
Owner: Developer
Status: planned
---

## Goal / value

After this task, `architecture_database_cache.md` is at most 200 lines and the claim about `sampling` reading through `database_cache` accurately reflects the current implementation.

## Context (contract mapping)

- Architecture doc: `nl_processing/database_cache/docs/architecture_database_cache.md` (currently 287 lines)
- Sampling implementation: `nl_processing/sampling/service.py` — reads from `ExerciseProgressStore` directly, NOT through `database_cache`
- Sampling architecture: `nl_processing/sampling/docs/architecture_sampling.md` — confirms dependency on `database`, no mention of `database_cache`

## Preconditions

- None — this task can be executed independently.

## Non-goals

- Do NOT change the sampling module code to read through `database_cache`.
- Do NOT modify any `.py` files.
- Do NOT remove any architectural decisions or data model definitions — only reduce verbosity.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**

- `nl_processing/database_cache/docs/architecture_database_cache.md`

**FORBIDDEN — this task must NEVER touch:**

- Any `.py` source or test file
- Any other doc file
- Any file outside `nl_processing/database_cache/docs/`

**Test scope:**

- Verification: `make check` must remain 100% green
- No new tests — this is a docs-only change

## Touched surface (expected files / modules)

- `nl_processing/database_cache/docs/architecture_database_cache.md`

## Dependencies and sequencing notes

- No dependencies. This file is not touched by any other task.

## Third-party / library research

N/A — no external dependencies.

## Implementation steps (developer-facing)

1. Open `nl_processing/database_cache/docs/architecture_database_cache.md` (287 lines).

2. **Fix the sampling claim** (lines 102-106). Current text:
   ```
   ### Decision: `sampling` Reads Through `database_cache`

   `sampling` should treat `database_cache.get_word_pairs_with_scores()` as its primary hot-path data source.

   **Rationale:** sampling needs low-latency access to both translated pairs and exercise-aware scores.
   ```

   Replace with:
   ```
   ### Decision: `sampling` Data Source

   `sampling` currently reads from `database` directly via `ExerciseProgressStore`. A future optimization may route sampling through `database_cache` for lower latency. The `database_cache` public API (`get_word_pairs_with_scores()`) is designed to support this transition without changes to the sampling interface.

   **Rationale:** sampling needs low-latency access to both translated pairs and exercise-aware scores, which `database_cache` can provide once wired.
   ```

3. **Reduce YAML frontmatter** (lines 1-20). The `inputDocuments` list is 7 entries. Trim it to the essential references only (keep the direct parent refs, remove the transitive ones):
   ```yaml
   inputDocuments:
     - nl_processing/database/docs/architecture_database.md
     - nl_processing/database_cache/docs/product-brief-database_cache-2026-03-07.md
   ```

4. **Tighten prose in decision sections.** For each decision block, remove filler sentences that repeat information stated in other decisions. Target cuts:
   - "Decision: Exercise Types Are Declared at Initialization" — remove the bullet list rationale if it duplicates the database architecture doc. Keep only the `database_cache`-specific implication.
   - "Decision: Stale-While-Revalidate Refresh Policy" — compress to essential behavior (3 numbered items are fine; remove surrounding prose if any).
   - "Decision: Local Writes Use Transactional Outbox + Auto-Flush" — the numbered list is essential; trim the explanatory paragraph after it to 2 sentences max.
   - "Decision: Refresh Rebuilds Snapshot Atomically" — keep the key fact (single transaction, no staging tables); remove redundant rationale if it repeats the outbox decision.

5. **Compact the Local Data Model tables.** The four tables are essential content — keep all columns. However, remove blank lines between table rows and any trailing whitespace to save lines.

6. **Compact the Lifecycle Flow section.** The numbered lists are essential — keep them but remove blank lines between sub-sections where possible.

7. **Compact the Test Strategy section.** Merge bullet lists more densely (combine Unit/Integration/E2E into a single section with sub-headers if needed, or just remove blank lines between bullet groups).

8. Count lines. Target: ≤200. If still over, look for additional prose that can be tightened without losing architectural decisions.

9. Verify `make check` still passes.

## Production safety constraints

N/A — documentation-only change.

## Anti-disaster constraints

- **Reuse before build**: modifying existing doc, not creating new files.
- **No regressions**: doc-only change; `make check` verifies no breakage.
- **Correct content**: the sampling claim must match the verified implementation.

## Error handling + correctness rules

N/A — documentation-only change.

## Zero legacy tolerance rule

After this task, the architecture doc no longer contains the inaccurate claim that sampling reads through `database_cache`. The corrected text reflects the actual implementation.

## Acceptance criteria (testable)

1. `architecture_database_cache.md` is ≤200 lines (verify with `wc -l`).
2. The sampling decision section accurately states that `sampling` currently reads from `database` directly and that `database_cache` is designed to support a future transition.
3. All architectural decisions are preserved (none removed).
4. All four local data model tables are preserved with all columns.
5. `make check` passes.
6. No `.py` files were modified.

## Verification / quality gates

- [ ] `wc -l nl_processing/database_cache/docs/architecture_database_cache.md` ≤ 200
- [ ] Sampling claim is accurate
- [ ] All decisions retained
- [ ] All data model tables retained
- [ ] `make check` passes
- [ ] No files outside `nl_processing/database_cache/docs/architecture_database_cache.md` were touched

## Edge cases

- The file must not be trimmed so aggressively that cross-references from the PRD or product brief break (no section headings should be renamed without checking references).

## Notes / risks

- **Risk**: Over-trimming may remove context needed by developers.
  - **Mitigation**: Only remove duplicated prose and verbose rationale. Keep every decision heading, every data model column, and every lifecycle step.
