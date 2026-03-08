---
Task ID: T5
Title: Reduce prd_database.md to ≤200 lines
Sprint: 2026-03-08_docs-impl-sync
Module: database (docs only)
Depends on: T1
Parallelizable: no (T1 modifies the same file first)
Owner: Developer
Status: planned
---

## Goal / value

After this task, `prd_database.md` is at most 200 lines while preserving all functional requirements, non-functional requirements, and the API surface definition. T1 adds FR41 first; this task then trims the file below the limit.

## Context (contract mapping)

- PRD: `nl_processing/database/docs/prd_database.md` (currently 259 lines, will be ~261 after T1 adds FR41)
- Repo convention: max 200 lines per file
- T1 must complete first because it adds content to this same file

## Preconditions

- T1 (add atomicity language to FR38 + new FR41) is complete.

## Non-goals

- Do NOT change the meaning of any functional requirement.
- Do NOT remove any FR or NFR.
- Do NOT modify any `.py` files.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**

- `nl_processing/database/docs/prd_database.md`

**FORBIDDEN — this task must NEVER touch:**

- Any `.py` source or test file
- Any other doc file

**Test scope:**

- Verification: `make check` must remain 100% green
- No new tests — this is a docs-only change

## Touched surface (expected files / modules)

- `nl_processing/database/docs/prd_database.md`

## Dependencies and sequencing notes

- Depends on T1 completing first — T1 modifies FR38 and adds FR41 in this same file.
- This task trims the file after T1's additions.

## Third-party / library research

N/A — no external dependencies.

## Implementation steps (developer-facing)

The file will be ~261 lines after T1. Need to remove ~65 lines. Strategy: trim verbose narrative sections and YAML frontmatter while keeping all FRs, NFRs, and API surface code blocks intact.

1. Open `nl_processing/database/docs/prd_database.md`.

2. **Trim YAML frontmatter** (lines 1-11). The `stepsCompleted` array lists 12 workflow steps. Compress to a single line if it's multi-line, or leave as-is if already single-line. Check for `classification` block — if verbose, compress:
   ```yaml
   classification: { projectType: developer_tool, domain: scientific, complexity: medium, projectContext: greenfield }
   ```
   This saves ~4 lines.

3. **Trim Executive Summary** (lines 20-27). Currently ~8 lines. Reduce to 4 lines by removing sentences that duplicate the product brief or are restated in "What Makes This Special":
   - Keep the first sentence defining the module.
   - Keep the sentence about exercise tables.
   - Remove prose about "not responsible for interactive low-latency access" (already in the product brief and architecture doc).

4. **Trim "What Makes This Special"** (lines 29-33). Currently 5 bullets. Remove the bullet about "Cache-facing internal APIs" — this is already covered by FR36-FR41 and the API surface section. Saves ~1 line.

5. **Trim Success Criteria** (lines 36-54). The measurable outcomes table has 5 rows. The table is fine — but remove the "Technical Success" bullet list above it if it duplicates the table. That's ~6 bullets. Replace with a single sentence: "Technical success is measured by the outcomes in the table below." Saves ~5 lines.

6. **Trim Scope section** (lines 56-64). The "Risk Mitigation" list has 3 bullets. Compress each bullet to one line (remove the explanatory clause after the colon if it restates an FR):
   - "Remote latency: delegated to `database_cache` (NFR1)."
   - "Exercise proliferation: declared at store initialization (FR29)."
   - "Async translation failures: logged, not propagated (FR20)."
   Saves ~3 lines.

7. **Trim User Journeys** (lines 66-86). Currently 4 journeys × ~4 lines each. Compress each to 2 lines max:
   - Journey 1: "Alex calls `add_words()` and gets `AddWordsResult` immediately. Background translation persists Russian words and links."
   - Journey 2: "Alex calls `get_words()` for translated `WordPair` items from the authoritative remote store."
   - Journey 3: "Alex configures `ExerciseProgressStore` with three exercise types. Each has its own dedicated remote score table."
   - Journey 4: "`database_cache` calls internal APIs to export snapshots and replay score deltas idempotently."
   Saves ~8 lines.

8. **Trim API Surface code blocks** (lines 92-148). The code blocks are essential — keep them. However, look for unnecessary blank lines within the code blocks and remove them. Also check if the comments inside the code can be shortened.

9. **Trim Implementation Considerations** (lines 155-161). Currently 5 bullets. Remove bullets that duplicate FRs:
   - Remove "`Word` from `core.models` remains the canonical word shape" (stated in architecture doc).
   - Remove "`database` owns remote durability and canonical IDs" (stated in executive summary).
   Saves ~2 lines.

10. **Compact FR sections.** Look for excessive blank lines between FR groups (Database Setup, Word Management, etc.) and remove them. Each group heading can be on the same line as the first FR if needed.

11. **Compact NFR section.** Merge NFR sub-headers into the NFR items to save lines:
    - Instead of "### Performance" followed by NFR1-NFR3, use "**Performance:** NFR1-NFR3" inline.
    - Same for Async, Reliability, Testing, Dependencies sub-sections.
    Saves ~5 lines per sub-header × 5 sub-headers = ~10 lines (accounting for the blank lines between them too, could save ~15 lines).

12. Count lines. Target: ≤200.

13. Verify `make check` still passes.

## Production safety constraints

N/A — documentation-only change.

## Anti-disaster constraints

- **Reuse before build**: modifying existing doc, not creating new files.
- **No regressions**: doc-only change; `make check` verifies no breakage.

## Error handling + correctness rules

N/A — documentation-only change.

## Zero legacy tolerance rule

After this task, the PRD is within the 200-line limit with no content loss.

## Acceptance criteria (testable)

1. `prd_database.md` is ≤200 lines (verify with `wc -l`).
2. All FRs (FR1-FR41, including the new FR41 from T1) are present and unchanged in meaning.
3. All NFRs (NFR1-NFR15) are present and unchanged in meaning.
4. The API surface code blocks are preserved.
5. `make check` passes.
6. No `.py` files were modified.

## Verification / quality gates

- [ ] `wc -l nl_processing/database/docs/prd_database.md` ≤ 200
- [ ] All FRs preserved (FR1-FR41)
- [ ] All NFRs preserved (NFR1-NFR15)
- [ ] API surface code blocks preserved
- [ ] `make check` passes
- [ ] No files outside `nl_processing/database/docs/prd_database.md` were touched

## Edge cases

- After T1 adds FR41, the numbering must remain consistent — verify FR41 appears after FR40 and no gaps exist.
- The NFR section restructuring (merging sub-headers) must not break any cross-references from other docs.

## Notes / risks

- **Risk**: 261→200 is a 61-line reduction — aggressive but achievable by targeting narrative prose, not requirements.
  - **Mitigation**: Steps above identify ~65 lines of cuttable prose. All FRs and NFRs are preserved verbatim.
