## Input discovery (requirements + architecture + prototype)

The scrum master reads three input sources:

### 1. Requirements
- Primary: `docs/requirements/`
- Fallback candidates:
  - `docs/req/`
  - `docs/prd.md`, `docs/*prd*.md`
  - `docs/product.md`, `docs/spec.md`, `docs/*requirements*.md`

### 2. Architecture
- Primary: `docs/architecture/`
- Especially: `docs/architecture/modules/` (module specs with interfaces)
- Especially: `docs/architecture/repository_layout.md` (directory ownership)
- Fallback candidates:
  - `docs/arch/`
  - `docs/*architecture*.md`
  - `docs/adr/` (ADRs)
  - `docs/decisions/`

### 3. Prototype codebase
- The entire repo source code — read to understand:
  - What currently exists for each module (mock? partial? nothing?).
  - Current code patterns and structure.
  - What needs to change vs. what can be preserved.
  - Existing test structure.

### Rules when inputs are missing

- If you cannot find requirements/architecture equivalents, do not invent them. Stop and report.
- The prototype codebase is always available (it's the repo itself).

## Allowed diffs (optional)

If git is available and you are asked to consider "what changed", limit diffs to:

- `git diff -- docs/requirements`
- `git diff -- docs/architecture`
- `git diff -- docs/sprints` (only for your own output validation)

Do not run unscoped diffs.

## Output discovery (where to write)

Write only under:

- `docs/sprints/<sprint_id>/...`

Create `docs/sprints/` if missing. Create one sub-directory per sprint:

- `docs/sprints/module-<name>/` for each module sprint
- `docs/sprints/tg-bot/` for the bot sprint
