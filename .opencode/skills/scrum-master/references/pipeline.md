## Scrum Master pipeline (autonomous by default)

Use this as the canonical planning pipeline. It produces one sprint per module + one sprint for the bot.

---

### Phase A — Full Intake (read everything)

1. **Read docs:**
   - Read every file in `docs/requirements/` fully — requirements, UX flow, constraints.
   - Read every file in `docs/architecture/` fully — tech stack, modules, patterns, interfaces, repository layout.
2. **Read the prototype codebase:**
   - Read all source code to understand current state: what exists, how it's structured, what patterns are used.
   - Identify what needs to change vs. what can be preserved.
3. **Extract module map:**
   - From `docs/architecture/modules/` — list every module, its responsibilities, interfaces, and dependencies.
   - From `docs/architecture/repository_layout.md` — identify the exact directory each module will live in.
   - From the prototype — understand what currently exists for each module (mock? partial? nothing?).
4. **Extract bot layer:**
   - From architecture — how the bot calls modules, handler structure, state management.
   - From the prototype — current handler code, routing, middleware.
5. **Build sprint roster:** List all sprints to create:
   - One sprint per module: `docs/sprints/module-<name>/`
   - One sprint for the bot: `docs/sprints/tg-bot/`

**Output:** Complete understanding of requirements, architecture, prototype, and a list of sprints to plan.

---

### Phase A2 — Validate Credentials & Integrations (with production safety)

Before planning, verify that all external services are accessible. **Critical: the current application version is running in production on this same machine (different directory). All validation and development must use testing/development resources only.**

1. **Identify all external services** from `docs/architecture/tech_stack.md` and module docs.
2. **Distinguish production vs. testing resources**: Confirm separate testing/development instances exist. If not, flag as a blocker.
3. **Check each required env var** is set and non-empty. Verify database connections point to testing databases.
4. **Make a lightweight validation call** for each service (testing instances only):
   - **HTTP APIs:** minimal authenticated request.
   - **Databases:** connect to testing database, run `SELECT 1`.
   - **Auth providers:** verify client credentials can obtain a token.
   - **Storage:** list buckets or attempt a small read.
5. **Verify resource isolation**: Confirm development config uses different ports, file paths, DB names than the production instance.
6. **If any credential is missing, invalid, or points to production:** stop immediately and report to the user.
7. **Do not proceed** until all integrations are confirmed working against testing/development resources.

**Output:** Confirmed working integrations (testing only) or a blocking report.

---

### Phase B — Deep Research (web search required)

Before writing tasks, research the technologies referenced in architecture:

1. **Identify all libraries, frameworks, and external APIs** from architecture docs.
2. **Web-search for each** to find:
   - Latest stable version and changelog.
   - Current official documentation URLs.
   - Recommended usage patterns and common pitfalls.
   - Breaking changes vs. architecture-specified versions.
3. **Search for API docs** of every external service. Get endpoint references, auth methods, rate limits, SDK recommendations.
4. **Collect documentation links** — embed directly into task files.
5. **Validate architecture assumptions** — if research reveals issues, note them. If significant, write a `CHANGE_PROPOSAL.md` inside the sprint folder.

**Rule:** Do not write tasks that reference a library or API without first researching its current state.

**Output:** Research notes for enriching every task.

---

### Phase C — Module Decomposition & Interface Extraction

This is the key planning phase that prepares for sprint-per-module creation.

1. **For each module in `docs/architecture/modules/`**, extract:
   - **Public interface** — exact function signatures, parameters, return types, error cases.
   - **Data models** — Pydantic models, types, enums.
   - **Dependencies** — what external services this module needs (APIs, databases, storage).
   - **Internal scope** — what files/directories this module owns.
   - **Test scope** — what test sub-directory this module creates (`tests/<module_name>/`).

2. **For the bot layer**, extract:
   - **Handler structure** — which handlers exist, what triggers them.
   - **Module usage** — how the bot calls each module's public interface.
   - **State management** — conversation states, user state, callback routing.
   - **Internal scope** — which files/directories the bot layer owns.
   - **Test scope** — `tests/bot/`.

3. **Build file ownership map** — assign every file/directory in the proposed repo layout to exactly one sprint:
   - Module `X` sprint owns: `src/<module_x>/` (or whatever the layout says) + `tests/<module_x>/`
   - Bot sprint owns: bot-level files + `tests/bot/`
   - Shared infrastructure: decide which sprint creates shared code (usually the first sprint in the dependency chain, or a dedicated foundation sprint).

4. **Identify inter-module dependencies** — if any module needs another module's interface for testing, plan stubs/mocks. No module sprint should import another module's implementation.

5. **Determine sprint ordering:**
   - Module sprints that have no inter-module dependencies → **fully parallel**.
   - If module A's interface is needed by module B's implementation → module A's interface definition task should be planned (but B can still use a stub).
   - Bot sprint can run in parallel if it uses interface stubs, or sequentially after all module sprints if it uses real modules.

**Output:** Sprint roster with file ownership, interface contracts, and inter-sprint dependencies.

---

### Phase D — Write Sprint Entrypoints

> **CRITICAL — location**: Create each sprint folder as `docs/sprints/<sprint_id>/`. NEVER place them elsewhere.

For each sprint in the roster, create `docs/sprints/<sprint_id>/SPRINT.md`:

- Goal, scope in/out, linked inputs.
- **Module scope** — which module (or bot) this sprint implements.
- **Boundary rules** — explicit ALLOWED / FORBIDDEN lists (files, directories, imports).
- **Test scope** — which test sub-dir this sprint creates and runs. The exact test command.
- **Interface contract** — the public interface this sprint must implement (for modules) or consume (for bot).
- Ordered task list + critical path.
- Parallel tracks within the sprint.
- Risks + mitigations.
- DoD including module isolation, test isolation, zero legacy tolerance.
- Production safety section.

**Task separation**: `SPRINT.md` is an index only. Every task lives in its own `TASK_*.md` file.

---

### Phase E — Write Tasks (sequentially, per sprint)

Process one sprint at a time. Within each sprint, create tasks **sequentially**:

1) Create **only the next task** file (start with T1).
2) **Self-validate** against `references/checklists.md` (A–G) and fix issues.
3) Use the **`task-checker` sub-agent** (via the Task tool) to independently review. Provide the task file path and `SPRINT.md` path.
4) If the task-checker reports problems, fix and re-submit until approved.
5) Only then proceed to the next task.

Every task must include:

- Explicit dependencies.
- **Module boundary constraints** — which files/dirs the task CAN and CANNOT touch.
- **Test scope** — tests go in `tests/<module_name>/` (or `tests/bot/`), run only those tests.
- Concrete verification (tests, linters, runtime checks).
- "Zero legacy tolerance" clause.
- "No silencing errors" clause.
- "Production safety" clause.
- Third-party research with doc links (mandatory for external dependencies).

**Standard tasks per module sprint:**
1. **Scaffold module directory** — create the module's directory structure per architecture layout.
2. **Scaffold test directory** — create `tests/<module_name>/` with `conftest.py` and initial test structure.
3. **Implement public interface** — implement the module's public interface as defined in architecture.
4. **Implement internal logic** — the module's core functionality, broken into sub-tasks as needed.
5. **Verify interface contract** — test that the module's public interface matches the architecture spec exactly.
6. **Error handling and edge cases** — implement error scenarios documented in requirements.

**Standard tasks per bot sprint:**
1. **Scaffold bot structure** — create handler files, middleware, state management per architecture.
2. **Scaffold test directory** — create `tests/bot/` with `conftest.py`.
3. **Implement handlers** — one task per major handler or flow group.
4. **Wire module interfaces** — connect handlers to module public interfaces (import and call).
5. **Verify UX flow** — test that the bot's user-facing behavior matches `docs/requirements/user_flow.md`.

---

### Phase F — Independent Review (per task, fresh context)

Run validation per task (see `references/checklists.md`):

1) Self-validate against the checklist (A–G).
2) Independent review via the **`task-checker` sub-agent** (Task tool, not bash/terminal).

- Verify completeness (no conditional clauses).
- Verify research done for 3rd-party deps.
- Verify module boundary constraints are present and correct.
- Verify test scope is correct (right sub-dir, right test command).
- Verify tasks are executable, ordered, dependency-aware, and parallel-safe.

Apply validation **per task as you create it**, then do a final full-pack pass before handoff.

---

### Phase G — Cross-Sprint Validation

After all sprints are created, validate consistency across sprints:

1. **File ownership check**: Verify no two sprints touch the same files/directories. Build a combined file ownership map and check for overlaps.
2. **Interface consistency**: Verify that the bot sprint's module interface usage matches what each module sprint implements.
3. **Test isolation check**: Verify each sprint's test scope is unique and no sprint runs another's tests.
4. **Shared code handling**: If multiple sprints need shared utilities, verify exactly one sprint creates them and others reference (not duplicate) them.
5. **Completeness check**: Verify that the combined sprints cover 100% of the architecture — no module or bot layer is missing.

---

### Phase H — Handoff

- Output is the set of sprint folders under `docs/sprints/`. Verify no files were created outside.
- **Explicitly confirm**: every sprint folder lives under `docs/sprints/<sprint_id>/`.
- Report the full sprint roster to the user:
  - List of all sprints created.
  - Which sprints can run in parallel vs. which have ordering dependencies.
  - Estimated scope per sprint.
  - Any blockers, risks, or change proposals.
- **If data model changes exist**: ensure each relevant sprint has migration instructions.
- **Resource isolation summary**: confirm all development planned against testing resources.

## Correct-course (change management)

If you discover mid-planning that the contract is wrong/insufficient:

- Do **not** edit requirements/architecture docs.
- Write a **Change Proposal** inside the relevant sprint folder (`CHANGE_PROPOSAL.md`) that includes:
  - Trigger + evidence.
  - Impact analysis.
  - Recommended path forward.
  - Which doc owners must apply which doc changes.
  - Updated task plan.
