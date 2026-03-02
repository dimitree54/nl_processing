## Template: `TASK_<task_slug>.md` (execution-ready)

Copy this template verbatim and fill in all placeholders.

---
Task ID: `<T#>`
Title: `<short>`
Sprint: `<sprint_id>`
Module: `<module name or "tg-bot">`
Depends on: `<T# list or —>`
Parallelizable: `<yes/no; if yes, with which task IDs>`
Owner: `Developer` (Scrum Master plans only)
Status: `planned`
---

## Goal / value

<1–2 sentences. What outcome must exist after this task?>

## Context (contract mapping)

- Requirements: `<link(s) to exact section(s)>`
- Architecture: `<link(s) to exact section(s)>`
- Module spec: `docs/architecture/modules/<module>.md`
- Related stories/epics (if any): `<links>`

## Preconditions

- <precondition>

## Non-goals

- <explicitly not doing>

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `<path/to/module/>` — module source code
- `tests/<module_name>/` — module tests
- <any other files explicitly owned by this sprint>

**FORBIDDEN — this task must NEVER touch:**
- Any other module’s code or tests
- <list specific forbidden paths>

**Test scope:**
- Tests go in: `tests/<module_name>/`
- Test command: `uv run pytest tests/<module_name>/ -x -v`
- NEVER run the full test suite or tests from other modules

## Touched surface (expected files / modules)

List likely areas. Do not be overly precise; be useful.

- <path or module>

## Dependencies and sequencing notes

- <why this depends on other tasks>
- <why it can/can’t run in parallel>

## Third-party / library research (mandatory for any external dependency)

For **every** 3rd-party library, API, or framework this task touches:

- **Library/API**: <name + exact version (verified via web search as latest stable)>
- **Official documentation**: <direct URL to the relevant docs page — not the homepage, the specific section>
- **API reference**: <URL to API/SDK reference for the specific methods/endpoints used>
- **Usage examples (verified current)**:
  - <concrete code snippet or pseudo-usage, verified against current docs — not from memory>
- **Known gotchas / breaking changes**: <any version-specific issues, migration notes, or common pitfalls found during research>
- **Rate limits / quotas** (if external API): <documented limits>

**Rules:**
- Never leave "check the docs" or "refer to documentation" as a placeholder — the actual links and patterns must be here.
- Never rely on training knowledge for API signatures — always verify via web search.
- Do not leave "if the library supports X …" conditional clauses — research and confirm.

## Implementation steps (developer-facing)

Write concrete steps. Avoid conditional branches. Avoid “TBD”.

1. <step>
2. <step>
3. <step>

## Production safety constraints (mandatory)

The current application version is **running in production on this same machine** (different directory). Shared local resources must not be disrupted.

- **Database operations**: All reads/writes must target the **testing/development database only**. Never connect to or modify the production database.
- **Resource isolation**: If this task uses files, ports, sockets, temp dirs, or log paths, explicitly confirm they do not collide with the production instance. Document the isolation strategy (different port, prefixed paths, separate config, etc.).
- **Migration preparation** (if this task changes the data model): Produce migration scripts/instructions as artifacts but **do not execute them against production**. These are delivered to the user in `MIGRATION_PLAN.md`.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: extend existing modules/utilities instead of duplicating functionality.
- **Correct libraries only**: use repo-approved libraries/versions (cite where the version comes from: lockfile, package manifest, or architecture doc).
- **Correct file locations**: follow repo structure and conventions; do not invent new top-level layouts without explicit architecture instruction.
- **No regressions**: identify what could break and ensure tests cover it.
- **Follow UX/spec** (if applicable): do not "approximate" UI behavior; cite the UX source.

## Error handling + correctness rules (mandatory)

- **Do not silence errors**:
  - No empty `catch`.
  - No blanket `try/catch` that discards exceptions.
  - No “return default” to mask failures unless explicitly required by requirements.
- **No mock fallbacks** unless explicitly required by requirements.
- Prefer failing fast with a clear error message over hiding failures.

## Zero legacy tolerance rule (mandatory)

After implementing this task:

- Remove or replace old code paths that are superseded.
- Avoid leaving dead code, deprecated paths, or “temporary” toggles.
- Avoid duplicating functionality; reuse existing implementations when possible.

## Acceptance criteria (testable)

Write criteria that can be verified.

1. <AC>
2. <AC>

## Verification / quality gates

Minimum gates (add repo-specific ones):

- [ ] Unit tests added/updated (where applicable)
- [ ] Integration/e2e tests updated (where applicable)
- [ ] Linters/formatters pass
- [ ] No new warnings introduced (unless explicitly accepted)
- [ ] Negative-path tests exist for important failures (esp. error handling)

## Edge cases

- <edge case>

## Rollout / rollback (if relevant)

- Rollout: <steps>
- Rollback: <steps>

## Notes / risks

- <risk + mitigation>
