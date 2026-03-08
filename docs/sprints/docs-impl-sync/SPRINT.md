---
Sprint ID: `2026-03-08_docs-impl-sync`
Sprint Goal: Fix all documentation-implementation discrepancies for the `database` and `database_cache` modules
Sprint Type: module
Module: database + database_cache (docs-only)
Status: planning
---

## Goal

Align every documentation file in `database/docs/` and `database_cache/docs/` with the actual implementation, enforce the repo 200-line-per-file limit, and remove stale leftover directories from a prior rename.

## Module Scope

### What this sprint fixes

- Documentation in `nl_processing/database/docs/` and `nl_processing/database_cache/docs/`
- Stale `__pycache__`-only directories from the old `database_cached` name
- Vulture whitelist accuracy (verified: no actual dead entries found)

### Boundary Rules (STRICTLY ENFORCED)

**ALLOWED — this sprint may ONLY touch:**

- `nl_processing/database/docs/prd_database.md` — PRD corrections and line-count reduction
- `nl_processing/database_cache/docs/architecture_database_cache.md` — line-count reduction, clarify sampling claim
- `nl_processing/database_cache/docs/prd_database_cache.md` — line-count reduction
- `.gitignore` — add entries for stale `database_cached` dirs (or document cleanup instructions)

**FORBIDDEN — this sprint must NEVER touch:**

- Any `.py` source file (no code logic changes)
- Any test file
- Any file outside the ALLOWED list above
- Requirements or architecture docs for modules other than `database` / `database_cache`

### Test Scope

- **Verification command**: `make check` (must remain 100% green)
- No new tests are added — this sprint is docs-only

## Verified Discrepancy Assessment

Before planning tasks, the scrum master audited every reported discrepancy against the actual codebase:

| # | Reported discrepancy | Verdict | Action |
|---|---|---|---|
| 1 | `architecture_database.md` shows `apply_score_delta` as non-atomic | **Already fixed** — lines 108, 119-126 correctly describe atomic behavior | None |
| 2 | Structure diagram missing `_neon_exercise.py` | **Already fixed** — line 146 lists it | None |
| 3 | PRD FR38 doesn't mention atomicity or delta validation | **Genuine** — FR38-40 omit transaction guarantee | T1 |
| 4 | `architecture_database_cache.md` is 287 lines (limit: 200) | **Genuine** | T2 |
| 5 | `prd_database_cache.md` is 221 lines (limit: 200) | **Genuine** | T3 |
| 6 | Architecture doc says "sampling reads through database_cache" but it doesn't | **Genuine** — sampling reads directly from `database` via `ExerciseProgressStore` | T2 |
| 7 | Stale `nl_processing/database_cached/` with `__pycache__` only | **Genuine** | T4 |
| 8 | Stale `tests/unit/database_cached/` with `__pycache__` only | **Genuine** | T4 |
| 9 | Vulture whitelist has dead `count_user_words` entries | **False** — `count_user_words` IS a method on both `AbstractBackend` (line 57) and `NeonBackend` (line 133) | None |
| 10 | `prd_database.md` is 259 lines (limit: 200) | **Genuine** (not in original report but discovered during audit) | T5 |

## Task list (dependency-aware)

- **T1:** `TASK_fix_prd_database_atomicity.md` (depends: —) (parallel: yes, with T2–T5) — Add atomicity and delta-validation language to FR38-40 in `prd_database.md`
- **T2:** `TASK_trim_arch_database_cache.md` (depends: —) (parallel: yes, with T1, T3–T5) — Reduce `architecture_database_cache.md` to ≤200 lines and clarify sampling claim
- **T3:** `TASK_trim_prd_database_cache.md` (depends: —) (parallel: yes, with T1, T2, T4, T5) — Reduce `prd_database_cache.md` to ≤200 lines
- **T4:** `TASK_cleanup_stale_dirs.md` (depends: —) (parallel: yes, with T1–T3, T5) — Remove stale `database_cached/` pycache directories
- **T5:** `TASK_trim_prd_database.md` (depends: T1) (parallel: no) — Reduce `prd_database.md` to ≤200 lines (after T1 modifies FR38)

## Dependency graph (DAG)

- T1 → T5
- T2, T3, T4 are independent

## Execution plan

### Critical path

- T1 → T5

### Parallel tracks (lanes)

- **Lane A**: T1 → T5
- **Lane B**: T2
- **Lane C**: T3
- **Lane D**: T4

## Production safety

This sprint modifies only documentation and removes stale `__pycache__` directories. No production database, configuration, or runtime code is touched.

- **Production database**: N/A — no data model or code changes
- **Shared resource isolation**: N/A — docs-only
- **Migration deliverable**: N/A — no data model changes

## Definition of Done (DoD)

All items must be true:

- ✅ All tasks completed and verified
- ✅ `make check` passes (100% green)
- ✅ No doc file exceeds 200 lines
- ✅ PRD FR38-40 accurately describe atomic score replay
- ✅ `architecture_database_cache.md` clarifies that sampling currently reads directly from `database`, not through `database_cache`
- ✅ Stale `database_cached/` directories are removed
- ✅ No `.py` source files were modified
- ✅ No files outside the ALLOWED list were touched

## Risks + mitigations

- **Risk**: Trimming docs below 200 lines may lose important content
  - **Mitigation**: Trim only YAML frontmatter bulk, duplicated context (shared-PRD refs), and verbose prose. Never remove requirements or architectural decisions.

- **Risk**: T1 (FR38 edit) and T5 (line trim) both touch `prd_database.md`
  - **Mitigation**: T5 depends on T1 — sequential execution prevents merge conflicts.

## Rollback / recovery notes

- All changes are documentation-only. Revert the relevant commit(s) to restore prior state.

## Sources used

- Architecture: `nl_processing/database/docs/architecture_database.md` (179 lines)
- PRD: `nl_processing/database/docs/prd_database.md` (259 lines)
- Architecture: `nl_processing/database_cache/docs/architecture_database_cache.md` (287 lines)
- PRD: `nl_processing/database_cache/docs/prd_database_cache.md` (221 lines)
- Code: `nl_processing/database/exercise_progress.py` — verified `apply_score_delta` is atomic
- Code: `nl_processing/database/backend/abstract.py` — verified `apply_score_delta_atomic` and `count_user_words` exist
- Code: `nl_processing/database/backend/neon.py` — verified `count_user_words` exists
- Code: `nl_processing/database/backend/_neon_exercise.py` — verified `atomic_apply_delta` implementation
- Code: `nl_processing/database/testing.py` — verified standalone `count_user_words` function
- Code: `nl_processing/sampling/service.py` — verified it reads from `ExerciseProgressStore` directly
- Code: `vulture_whitelist.py` — verified all entries are valid
- Stale dirs: `nl_processing/database_cached/` and `tests/unit/database_cached/` — confirmed `__pycache__` only
