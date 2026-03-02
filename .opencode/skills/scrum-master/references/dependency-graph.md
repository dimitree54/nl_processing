## Dependency graph (DAG) + parallelization lanes

Build a dependency graph so the sprint is executable and parallelizable without conflicts.

### Step 1 — Define task nodes

For each task, define:

- **Inputs**: docs sections, existing modules, existing interfaces, existing data.
- **Outputs**: new/changed modules, migrations, endpoints, UI flows, tests, docs (note: Scrum Master does not edit requirements/architecture).
- **Touched surface**: likely files/directories (coarse is fine).

### Step 2 — Define edges (dependencies)

Create edges when:

- A task produces an artifact another task needs (schema, API contract, shared module).
- Two tasks compete over the same core files or schema (serialize to avoid merge conflicts).
- A task requires infrastructure setup (DB, secrets, vendor account) before it can run.

### Step 3 — Derive lanes

Group tasks into lanes that can run concurrently:

- **Lane A (foundation)**: schema/migrations, core interfaces, shared utilities.
- **Lane B (feature slice 1)**: a vertical slice that depends on Lane A.
- **Lane C (feature slice 2)**: independent vertical slice (only if file conflicts are unlikely).
- **Lane QA**: tests, harnesses, fixtures (parallelize where safe).

### Notation (keep it simple)

Use this notation in `SPRINT.md`:

- **T1 → T3** means “T3 depends on T1”.
- **Parallel: T4 || T5** means “T4 and T5 can be done concurrently”.

### Safety rules

- Prefer fewer, safer lanes over “maximum parallelism”.
- If unsure about file-level contention, serialize.
- Never hide dependencies “in someone’s head”: write them in the task headers.
