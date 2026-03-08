---
Task ID: T3
Title: Reduce prd_database_cache.md to ≤200 lines
Sprint: 2026-03-08_docs-impl-sync
Module: database_cache (docs only)
Depends on: —
Parallelizable: yes, with T1, T2, T4, T5
Owner: Developer
Status: planned
---

## Goal / value

After this task, `prd_database_cache.md` is at most 200 lines while preserving all functional requirements, non-functional requirements, and the API surface definition.

## Context (contract mapping)

- PRD: `nl_processing/database_cache/docs/prd_database_cache.md` (currently 221 lines — 21 lines over limit)

## Preconditions

- None — this task can be executed independently.

## Non-goals

- Do NOT change the meaning of any functional requirement.
- Do NOT remove any FR or NFR.
- Do NOT modify any `.py` files.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**

- `nl_processing/database_cache/docs/prd_database_cache.md`

**FORBIDDEN — this task must NEVER touch:**

- Any `.py` source or test file
- Any other doc file

**Test scope:**

- Verification: `make check` must remain 100% green
- No new tests — this is a docs-only change

## Touched surface (expected files / modules)

- `nl_processing/database_cache/docs/prd_database_cache.md`

## Dependencies and sequencing notes

- No dependencies. This file is not touched by any other task.

## Third-party / library research

N/A — no external dependencies.

## Implementation steps (developer-facing)

The file is 21 lines over the 200-line limit. The goal is to remove ~25 lines of non-essential prose without losing any requirement.

1. Open `nl_processing/database_cache/docs/prd_database_cache.md` (221 lines).

2. **Trim YAML frontmatter** (lines 1-11). The `stepsCompleted` array is verbose. Compress it to a single line:
   ```yaml
   stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-02b-vision', 'step-02c-executive-summary', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
   ```
   This is already on one line — so no savings here. Instead, look at the body.

3. **Trim the Executive Summary** (lines 20-27). This is 8 lines of prose. Reduce to 4-5 lines by removing the sentence that restates the TTL behavior (already covered in FR5-FR7):
   - Remove: "If the local snapshot is older than the configured TTL, the module immediately serves the existing snapshot and starts a background refresh."
   - This is duplicated by FR5, FR6, and Journey 1.

4. **Trim Scope section** (lines 47-55). The "Risk Mitigation" bullets restate Journey 4 and FR7/FR13. Compress to 2 bullets max:
   ```
   - **Cold start:** cache reports not-ready instead of returning empty data (FR7, FR13).
   - **Remote outage + exercise drift:** local writes are queued; changed exercise set triggers rebuild (FR26, FR30).
   ```

5. **Trim User Journeys** (lines 57-73). Journey 3 and Journey 4 contain prose that duplicates FR14-FR20 and FR25-FR26. Shorten each journey to 2 sentences max:
   - Journey 3: "The user answers incorrectly. `record_exercise_result()` updates the local score immediately, queues a sync event, and starts a background flush (fire-and-forget)."
   - Journey 4: "Neon is unreachable. The flush fails but events stay pending; the next `record_exercise_result()` retries them automatically."

6. **Trim Implementation Considerations** (lines 129-136). Remove bullets that duplicate the executive summary or FRs:
   - Remove: "`database_cache` is a downstream consumer of `database`" (stated in executive summary)
   - Remove: "`exercise_types` are configured once at initialization and reused throughout the object lifetime" (stated in FR2, FR3)

7. **Remove excess blank lines.** Scan for consecutive blank lines and reduce to single blank lines.

8. Count lines. Target: ≤200. If still over 200, further compress the Success Criteria table prose.

9. Verify `make check` still passes.

## Production safety constraints

N/A — documentation-only change.

## Anti-disaster constraints

- **Reuse before build**: modifying existing doc, not creating new files.
- **No regressions**: doc-only change; `make check` verifies no breakage.

## Error handling + correctness rules

N/A — documentation-only change.

## Zero legacy tolerance rule

After this task, no verbose duplicate prose remains in the PRD. All FRs and NFRs are preserved.

## Acceptance criteria (testable)

1. `prd_database_cache.md` is ≤200 lines (verify with `wc -l`).
2. All FRs (FR1-FR34) are present and unchanged in meaning.
3. All NFRs (NFR1-NFR14) are present and unchanged in meaning.
4. The API surface code block is preserved.
5. `make check` passes.
6. No `.py` files were modified.

## Verification / quality gates

- [ ] `wc -l nl_processing/database_cache/docs/prd_database_cache.md` ≤ 200
- [ ] All FRs preserved
- [ ] All NFRs preserved
- [ ] API surface block preserved
- [ ] `make check` passes
- [ ] No files outside `nl_processing/database_cache/docs/prd_database_cache.md` were touched

## Edge cases

- Be careful not to accidentally merge two FRs into one — each FR must remain individually numberable and testable.

## Notes / risks

- **Risk**: Trimming journeys too aggressively may reduce clarity for new contributors.
  - **Mitigation**: Keep at least one sentence per journey that describes the user's action and the system's response. The FRs provide the authoritative detail.
