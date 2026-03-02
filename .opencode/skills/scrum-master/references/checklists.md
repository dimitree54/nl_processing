## Quality gates (before finishing a sprint plan)

Use this checklist before you stop.

### A) Scope + contract integrity

- [ ] All planning is grounded in `docs/requirements/` + `docs/architecture/` + prototype codebase.
- [ ] No edits were made to requirements/architecture.
- [ ] All outputs live under `docs/sprints/<sprint_id>/`.
- [ ] **Sprint location verified**: `SPRINT.md` and ALL `TASK_*.md` files are inside `docs/sprints/<sprint_id>/` — NOT at repo root, NOT directly in `docs/`, NOT in `docs/requirements/`, NOT in `docs/architecture/`, NOT anywhere else.

### B) Task executability (no “conditional tasks”)

The sprint must not contain lazy conditionals like:

- “If the library supports X, do Y…”
- “If the app already has A, then…”

Instead:

- Do the research now and pick the correct approach, or
- Write a dedicated research/prep task, or
- Create `WEB_RESEARCH.md` with a self-contained request and block the dependent tasks until research is complete.

### B2) Task separation (no inlined tasks)

- [ ] `SPRINT.md` contains only the task list (IDs + links + brief labels) and plan metadata.
- [ ] No task bodies are inlined into `SPRINT.md`. Every task has its own `TASK_*.md` file.
- [ ] Every `TASK_*.md` is referenced from `SPRINT.md`.

### C) Dependency + parallel safety

- [ ] Every task declares dependencies (or explicitly states none).
- [ ] Parallel lanes are justified (low file contention; artifacts don’t conflict).
- [ ] Critical path is explicit.

### D) Zero legacy tolerance + "no silenced errors" coverage


**Post-sprint outcome**: codebase must be **100% in sync** with requirements and architecture; no legacy residue.


- [ ] Every task that changes behavior includes “remove superseded paths / dead code”.
- [ ] If refactoring is needed to eliminate legacy, it is **planned explicitly** as dedicated tasks (not deferred).
- [ ] Every task that touches error handling forbids swallow/ignore patterns and forbids mock fallbacks unless required.

### E) Production safety + resource isolation

- [ ] No task connects to, reads from, or writes to the **production database**. All DB operations target testing/development databases only.
- [ ] Tasks that use shared local resources (files, ports, sockets, temp dirs, log paths) explicitly document how they avoid collisions with the **co-located production instance**.
- [ ] If data model changes exist, a `MIGRATION_PLAN.md` is included with: migration steps, backup instructions, rollback procedures, validation queries, and downtime recommendations.
- [ ] Migration plan is clearly marked as a **user-reviewed deliverable** — never auto-executed.
- [ ] Dev/test configuration is explicitly separated from production configuration (different DB names, ports, file paths).

### F) Module isolation + test scope

- [ ] Every sprint declares its **module scope** (ALLOWED / FORBIDDEN file lists).
- [ ] Every task declares its **module boundary constraints** (ALLOWED / FORBIDDEN).
- [ ] Every task specifies its **test scope** — which test sub-dir it writes to and the exact test command.
- [ ] No task runs the full test suite — only the sprint's own tests.
- [ ] No two sprints touch the same files/directories (cross-sprint check).
- [ ] Module sprints do not import from other modules (only from own code + external libraries).
- [ ] Bot sprint imports only from module public interfaces, never module internals.
- [ ] If a module needs another module's interface for testing, a stub/mock is planned — not the real module.

### G) Verification completeness

- [ ] Every task has testable acceptance criteria.
- [ ] Sprint DoD requires module-scoped tests + lint/quality checks green.
- [ ] Tasks list likely files/modules affected.

## Task validation — REQUIRED (self-validate + task-checker)

**REQUIRED**: Validate **EACH TASK SEPARATELY AND INDEPENDENTLY**.

**Sequential creation rule**: create `T1` + `TASK_*.md`, validate/iterate until approved, then create `T2`, etc. Do **not** write all tasks first and validate at the end.

For each `TASK_*.md`:

1) **Self-validate** against this checklist (A–G) and fix issues.
2) **Independent review via `task-checker` sub-agent** (do NOT use bash/terminal): launch the `task-checker` sub-agent and provide:

- The path to `docs/sprints/<sprint_id>/TASK_<slug>.md`
- The path to `docs/sprints/<sprint_id>/SPRINT.md` (for dependency context)

Suggested `task-checker` prompt (adapt paths as needed):

"Review `docs/sprints/<sprint_id>/TASK_<slug>.md` for completeness, clarity, dependency correctness, acceptance criteria quality, file/module coverage, and missing prerequisites/research. Use `docs/sprints/<sprint_id>/SPRINT.md` for dependency context. Return an approval or a concrete fix list."

**Each task review must assess independently:**
- Task completeness and clarity
- Dependency declarations
- Acceptance criteria quality
- File/module coverage
- Missing prerequisites or research

If the task-checker requests fixes, apply them by editing only the sprint files, then re-run the task-checker until approved.
