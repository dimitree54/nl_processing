## Template: `SPRINT.md`

Copy this template verbatim and fill in all placeholders.

---
Sprint ID: `<YYYY-MM-DD_short-slug>`
Sprint Goal: `<1 sentence>`
Sprint Type: `<module | bot>`
Module: `<module name or "tg-bot">`
Status: `planning`
Owners: `<optional>`
---

## Goal

<1–3 sentences. Be concrete.>

## Module Scope

### What this sprint implements
- Module: `<module name>` (or "Telegram bot layer")
- Architecture spec: `docs/architecture/modules/<module>.md` (or bot section)

### Boundary Rules (STRICTLY ENFORCED)

**ALLOWED — this sprint may ONLY touch:**
- `<path/to/module/>` — module source code
- `tests/<module_name>/` — module tests
- <any other files explicitly owned by this sprint>

**FORBIDDEN — this sprint must NEVER touch:**
- Any other module's code or tests
- <list specific forbidden paths>
- The full test suite (only run `tests/<module_name>/`)

### Test Scope
- **Test directory**: `tests/<module_name>/`
- **Test command**: `uv run pytest tests/<module_name>/ -x -v`
- **NEVER run**: `uv run pytest` (full suite) or tests from other modules

## Interface Contract

### Public interface this sprint implements (for module sprints)
```python
# Copy from docs/architecture/modules/<module>.md
async def function_name(param: Type) -> ReturnType:
    ...
```

### Module interfaces this sprint consumes (for bot sprint)
- `<module_name>.function_name()` — from `docs/architecture/modules/<module>.md`

## Scope

### In
- <bullet>

### Out
- <bullet>

## Inputs (contracts)

- Requirements: `<link(s) into docs/requirements/...>`
- Architecture: `<link(s) into docs/architecture/...>`
- Module spec: `docs/architecture/modules/<module>.md`
- Related constraints/ADRs: `<links>`

## Change digest

Summarize what changed and why it matters. If there were no changes, summarize the current baseline contract.

- **Requirement deltas**:
  - <delta>
- **Architecture deltas**:
  - <delta>

## Task list (dependency-aware)

Use stable IDs `T1`, `T2`, ... and link each file.

**Rule**: Do **not** inline full task instructions in `SPRINT.md`. Every task has its own `TASK_*.md` file.

- **T1:** `TASK_<slug>.md` (depends: —) (parallel: no) — <short label>
- **T2:** `TASK_<slug>.md` (depends: T1) (parallel: yes, with T3) — <short label>
- **T3:** `TASK_<slug>.md` (depends: T1) (parallel: yes, with T2) — <short label>

## Dependency graph (DAG)

- T1 → T2
- T1 → T3

## Execution plan

### Critical path
- T1 → T2 → T4

### Parallel tracks (lanes)
- **Lane A**: T1, T2
- **Lane B**: T3, T5

## Production safety

The current application version is **running in production on this same machine** (different directory).

- **Production database**: NOT modified during this sprint. All development uses testing/development databases.
- **Shared resource isolation**: <describe how dev instance avoids collisions with production: ports, file paths, DB names, temp dirs, etc.>
- **Migration deliverable**: <`MIGRATION_PLAN.md` path or "N/A — no data model changes">

## Definition of Done (DoD)

All items must be true:

- ✅ All tasks completed and verified
- ✅ Module tests pass: `uv run pytest tests/<module_name>/ -x -v`
- ✅ Module isolation: no files outside the ALLOWED list were touched
- ✅ Public interface matches architecture spec exactly
- ✅ Zero legacy tolerance (dead code removed; codebase in sync with docs)
- ✅ No errors are silenced (no swallowed exceptions)
- ✅ Requirements/architecture docs unchanged
- ✅ Production database untouched; all development against testing DB only
- ✅ No shared local resources conflict with production instance
- ✅ Migration plan delivered to user (if data model changes exist)

## Risks + mitigations

- **Risk**: <risk>
  - **Mitigation**: <mitigation>

## Migration plan (if data model changes)

Path: `docs/sprints/<sprint_id>/MIGRATION_PLAN.md` (or "N/A" if no data model changes)

## Rollback / recovery notes

- <what to do if this sprint's changes must be reverted>

## Task validation status

- Per-task validation order: `T1` → `T2` → `T3` → ...
- Validator: `<task-checker>`
- Outcome: `<approved | changes requested>`
- Notes: `<short>`

## Sources used

- Requirements: <paths read>
- Architecture: <paths read>
- Module spec: <path>
- Code read (for scoping only): <paths read>

## Contract summary

### What (requirements)
- <bullet>

### How (architecture)
- <bullet>

## Impact inventory (implementation-facing)

- **Module**: <module name and directory>
- **Interfaces**: <public functions>
- **Data model**: <entities owned by this module>
- **External services**: <APIs/services this module calls>
- **Test directory**: `tests/<module_name>/`
