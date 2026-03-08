---
Task ID: T4
Title: Remove stale database_cached pycache directories
Sprint: 2026-03-08_docs-impl-sync
Module: database + database_cache (cleanup)
Depends on: —
Parallelizable: yes, with T1, T2, T3, T5
Owner: Developer
Status: planned
---

## Goal / value

After this task, the stale `nl_processing/database_cached/` and `tests/unit/database_cached/` directories (which contain only `__pycache__/` from a prior module rename) are deleted, removing confusion for contributors who might mistake them for active module directories.

## Context (contract mapping)

- The module was renamed from `database_cached` to `database_cache` during development.
- The old directories were left behind with only `__pycache__/` contents.
- These directories are untracked by git (`.gitignore` covers `__pycache__/`), so they only exist on the local filesystem.
- Current contents verified:
  - `nl_processing/database_cached/__pycache__/` — 13 `.pyc` files
  - `tests/unit/database_cached/__pycache__/` — 8 `.pyc` files

## Preconditions

- None — this task can be executed independently.

## Non-goals

- Do NOT modify any `.py` source files.
- Do NOT modify `.gitignore` — it already covers `__pycache__/` which is sufficient.
- Do NOT delete any tracked files.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY:**

- Delete the untracked directories `nl_processing/database_cached/` and `tests/unit/database_cached/`

**FORBIDDEN — this task must NEVER touch:**

- Any tracked file in the repository
- Any `.py` source or test file
- The active `nl_processing/database_cache/` module
- The active `tests/unit/database_cache/` test directory (if it exists)

**Test scope:**

- Verification: `make check` must remain 100% green
- No new tests — this is a cleanup task

## Touched surface (expected files / modules)

- `nl_processing/database_cached/` (delete entire directory)
- `tests/unit/database_cached/` (delete entire directory)

## Dependencies and sequencing notes

- No dependencies. These directories are untracked and contain only `__pycache__/`.

## Third-party / library research

N/A — no external dependencies.

## Implementation steps (developer-facing)

1. Verify the directories contain only `__pycache__/`:
   ```bash
   ls -la nl_processing/database_cached/
   ls -la tests/unit/database_cached/
   ```
   Both should show only a `__pycache__/` subdirectory.

2. Delete the stale directories:
   ```bash
   rm -rf nl_processing/database_cached/
   rm -rf tests/unit/database_cached/
   ```

3. Verify deletion:
   ```bash
   ls nl_processing/database_cached/ 2>&1  # should report "No such file or directory"
   ls tests/unit/database_cached/ 2>&1     # should report "No such file or directory"
   ```

4. Verify `make check` still passes — these directories were untracked so removal should have zero impact.

5. Verify `git status` shows no changes (the directories were not tracked).

## Production safety constraints

N/A — deleting untracked `__pycache__` directories has no production impact. The production instance runs from a different directory.

## Anti-disaster constraints

- **Verify before deleting**: step 1 confirms only `__pycache__/` exists. If any non-`__pycache__` content is found, stop and report.
- **No regressions**: `make check` verifies no breakage.

## Error handling + correctness rules

N/A — filesystem cleanup only.

## Zero legacy tolerance rule

After this task, no remnants of the old `database_cached` module name remain on the filesystem.

## Acceptance criteria (testable)

1. `nl_processing/database_cached/` does not exist.
2. `tests/unit/database_cached/` does not exist.
3. `git status` shows no new changes (directories were untracked).
4. `make check` passes.
5. No tracked files were modified.

## Verification / quality gates

- [ ] Both stale directories are deleted
- [ ] `git status` clean (no tracked-file changes)
- [ ] `make check` passes

## Edge cases

- If someone has re-created these directories with actual `.py` files since the audit, step 1 will catch this. In that case, stop and report instead of deleting.

## Notes / risks

- **Risk**: Extremely low — these are untracked `__pycache__` directories from a stale module name.
