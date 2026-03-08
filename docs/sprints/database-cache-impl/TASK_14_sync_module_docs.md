---
Task ID: T14
Title: Review and fix `database_cache/docs/` to match implementation
Sprint: 2026-03-08_database-cache-impl
Module: database_cache
Depends on: T8
Parallelizable: yes, with T9, T10, T11, T12, T13
Owner: Developer
Status: planned
---

## Goal / value

Review the three existing design documents in `nl_processing/database_cache/docs/` and update them to accurately reflect the implementation. Fix any discrepancies between the architecture/PRD docs and what was actually built. Ensure the docs are the canonical reference for the implemented module.

## Context (contract mapping)

- Product brief: `nl_processing/database_cache/docs/product-brief-database_cache-2026-03-07.md`
- PRD: `nl_processing/database_cache/docs/prd_database_cache.md`
- Architecture: `nl_processing/database_cache/docs/architecture_database_cache.md`
- These were written BEFORE implementation — there may be minor deviations in:
  - Method signatures or parameter names
  - Internal file organization if 200-line limits forced decomposition
  - Model fields if `CacheStatus` gained/lost attributes
  - Error handling details

## Preconditions

- T8 complete (all module source files exist — needed to compare docs against actual implementation)

## Non-goals

- Rewriting docs from scratch
- Changing the architecture or requirements
- Updating shared docs (that's T13)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/database_cache/docs/product-brief-database_cache-2026-03-07.md`
- `nl_processing/database_cache/docs/prd_database_cache.md`
- `nl_processing/database_cache/docs/architecture_database_cache.md`

**FORBIDDEN — this task must NEVER touch:**
- Any module source code
- Any test files
- Any shared docs (those are T13)

**Test scope:**
- No tests to write for this task
- Verification: `make check` passes

## Touched surface (expected files / modules)

- `nl_processing/database_cache/docs/product-brief-database_cache-2026-03-07.md`
- `nl_processing/database_cache/docs/prd_database_cache.md`
- `nl_processing/database_cache/docs/architecture_database_cache.md`

## Dependencies and sequencing notes

- Depends on T8 (module must be implemented to compare docs against reality)
- Can run in parallel with T9–T13
- Order-independent — doc updates don't affect tests or code

## Third-party / library research (mandatory for any external dependency)

- No third-party libraries involved — documentation review only.

## Implementation steps (developer-facing)

1. **Read all three design docs** and the actual implementation (all 7 source files).

2. **Compare and fix discrepancies** in each document:

   ### `architecture_database_cache.md`:
   - Verify "Module Internal Structure" file list matches actual files created.
   - Verify SQLite table schemas match the actual DDL in `local_store.py`.
   - Verify "Remote Integration Contract" code examples match actual `ExerciseProgressStore` API usage.
   - Verify "Lifecycle Flow" descriptions match actual `service.py` logic.
   - Update any method signatures or class names that changed during implementation.

   ### `prd_database_cache.md`:
   - Verify API surface code examples match actual `DatabaseCacheService` method signatures.
   - Verify `CacheStatus` field list matches actual `models.py`.
   - Verify exception names and descriptions match actual `exceptions.py`.
   - Verify FR statements are still accurate against implementation.
   - Mark any FRs that were implemented differently with a note.

   ### `product-brief-database_cache-2026-03-07.md`:
   - Verify "Core Features" list is accurate.
   - Verify "Module-Specific Dependencies" reflects actual dependencies.
   - Generally this document is high-level and less likely to need changes.

3. **Specific items to check**:
   - Does `CacheStatus` have all the fields listed in the PRD? Did any fields get added or renamed?
   - Does the constructor accept `cache_dir` (optional parameter added during implementation)?
   - Are there any additional helper methods that should be documented?
   - Does `get_words()` return `list[WordPair]` (not `list[dict]`)?
   - Does the test strategy section still accurately describe the test structure?

4. Run `make check` to ensure no issues.

## Production safety constraints (mandatory)

- **Database operations**: N/A — documentation only.
- **Resource isolation**: N/A.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Editing existing docs, not creating new ones.
- **Correct file locations**: Only touching files in `nl_processing/database_cache/docs/`.
- **No regressions**: Doc changes don't affect runtime.

## Error handling + correctness rules (mandatory)

- N/A — documentation changes.

## Zero legacy tolerance rule (mandatory)

- Remove any references to approaches that were not implemented (e.g., if the architecture proposed staging tables for atomic rebuild but the implementation used a different approach).
- Ensure no stale code examples that don't match actual API.

## Acceptance criteria (testable)

1. All three docs accurately reflect the implemented module.
2. API code examples in the PRD work against the actual implementation (method names, parameters, return types match).
3. `CacheStatus` fields in docs match `models.py`.
4. SQLite table schemas in architecture doc match `local_store.py` DDL.
5. No references to unimplemented features without a "Future Vision" qualifier.
6. `make check` passes.

## Verification / quality gates

- [ ] Each doc reviewed against actual implementation
- [ ] Code examples verified against actual module API
- [ ] `make check` passes
- [ ] No stale/incorrect information remains

## Edge cases

- If implementation deviated significantly from architecture (e.g., split a file for 200-line limit), document the actual structure.
- If additional methods were added to `LocalStore` or `CacheSyncer` during implementation, add them to the architecture doc.

## Notes / risks

- **Risk**: Documentation drift is hard to detect automatically.
  - **Mitigation**: Systematic comparison: for each code example in docs, verify it runs against the actual code. For each table schema in docs, verify it matches the DDL.
- This task is best done after implementation is complete and stable (after T8), even though it can technically run in parallel with tests.
