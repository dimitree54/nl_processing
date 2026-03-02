---
Task ID: `T7`
Title: `Final verification: make check passes`
Sprint: `2026-03-02_module-core`
Module: `core`
Depends on: `T3, T4, T5, T6`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Run the full `make check` pipeline and fix any remaining issues so that the entire quality gate passes. This is the sprint's Definition of Done gate — after this task, ruff format, ruff check, pylint, vulture, jscpd, and all pytest suites (unit, integration, e2e) pass cleanly. Update `vulture_whitelist.py` if needed to suppress false positives from the new core code.

## Context (contract mapping)

- Requirements: `docs/planning-artifacts/prd.md` — SNFR5 (100% test pass rate)
- Architecture: `docs/planning-artifacts/architecture.md` — "Quality Gate: `make check`"
- Related: `Makefile` — defines the full `make check` pipeline

## Preconditions

- T1 through T6 all completed
- All core source files exist: `models.py`, `exceptions.py`, `prompts.py`, `scripts/prompt_author.py`
- All core test files exist: `test_models.py`, `test_exceptions.py`, `test_prompts.py`
- Legacy cleanup done (T1), dependencies installed (T2)

## Non-goals

- No new feature implementation — only fixes to pass `make check`
- No changes to `Makefile`, `ruff.toml`, or `pytest.ini`
- No fixing issues in other modules' files (e.g., `extract_text_from_image/`) — only files owned by this sprint

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `vulture_whitelist.py` (modify — add false-positive suppressions if needed)
- Any file in the ALLOWED list from the SPRINT.md — but only to fix issues discovered during `make check`
- Specifically: `nl_processing/core/`, `tests/unit/core/`, and the legacy cleanup files from T1

**FORBIDDEN — this task must NEVER touch:**
- `nl_processing/extract_text_from_image/` — owned by another sprint
- `tests/unit/extract_text_from_image/` — owned by another sprint
- `Makefile`, `ruff.toml`, `pytest.ini`
- Any docs outside `docs/sprints/module-core/`
- Requirements/architecture docs

**Test scope:**
- Run the full `make check` pipeline
- All steps must pass: `ruff format`, `ruff check`, `pylint`, `vulture`, `jscpd`, `pytest unit`, `pytest integration`, `pytest e2e`
- Note: `make check` runs ALL tests across the project, not just core's. If `extract_text_from_image` tests fail due to their own broken state (owned by another sprint), that is a known issue — document it but do not fix their files.

## Touched surface (expected files / modules)

- `vulture_whitelist.py` — may need updates for false positives
- Possibly minor fixes to core files if `make check` reveals issues

## Dependencies and sequencing notes

- Depends on all previous tasks (T1-T6) — everything must be in place
- This is the final task — no other task depends on it within this sprint
- Must run sequentially after all other tasks complete

## Third-party / library research (mandatory for any external dependency)

N/A — this task uses only existing tools (`make check` pipeline).

## Implementation steps (developer-facing)

1. **Run `make check`** (or `doppler run -- make check` if API keys are needed for integration/e2e tests):
   ```bash
   make check
   ```
2. **Analyze any failures** — categorize each failure as:
   - (a) Owned by this sprint → fix it
   - (b) Owned by another sprint (e.g., `extract_text_from_image` broken test) → document but do not fix
   - (c) Pre-existing issue unrelated to this sprint → document but do not fix

3. **Fix owned failures** — common issues to expect:
   - **vulture false positives**: If vulture flags functions/variables in `prompt_author.py` or test fixtures as unused, add them to `vulture_whitelist.py`
   - **ruff format**: Run `uv run ruff format` to auto-fix
   - **ruff check**: Run `uv run ruff check --fix` to auto-fix, then manually fix any remaining issues
   - **pylint 200-line limit**: If any core file exceeds 200 lines, decompose
   - **jscpd code duplication**: If test files have too much duplication, refactor

4. **Update `vulture_whitelist.py`** if needed:
   ```python
   # Vulture whitelist — list false-positive "unused" symbols here.
   # Add any symbols vulture incorrectly flags as unused.
   ```
   If specific symbols need whitelisting, import them in the whitelist file following the existing pattern.

5. **Re-run `make check`** until all steps pass (or only known external failures remain).

6. **Document known failures from other sprints** — if `make check` fails due to files owned by other sprints (e.g., `nl_processing/extract_text_from_image/__init__.py` is not empty, `tests/unit/extract_text_from_image/test_extract_text_from_image.py` has broken imports), note them here as expected.

## Production safety constraints (mandatory)

- **Database operations**: None.
- **Resource isolation**: `make check` runs locally in the dev environment. No production resources accessed.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Only fix issues — no new features.
- **Correct libraries only**: No new dependencies.
- **Correct file locations**: Only modify files within the sprint's ALLOWED list.
- **No regressions**: Fixes must not break anything that was previously working.

## Error handling + correctness rules (mandatory)

- Do not suppress linter errors with `noqa` unless absolutely necessary and documented.
- Do not skip tests — fix them.
- Do not add empty `except` blocks to silence errors.

## Zero legacy tolerance rule (mandatory)

- All dead code flagged by vulture in sprint-owned files must be removed or whitelisted with justification.
- No "temporary" workarounds — either fix properly or document as a known issue from another sprint.

## Acceptance criteria (testable)

1. `uv run ruff format` produces no changes (already formatted)
2. `uv run ruff check` produces no errors in sprint-owned files
3. `uvx pylint nl_processing/core/ tests/unit/core/ --disable=all --enable=C0302 --max-module-lines=200` passes
4. `uv run vulture nl_processing tests vulture_whitelist.py` produces no errors in sprint-owned files
5. `npx jscpd --exitCode 1` passes
6. `uv run pytest tests/unit/core/ -x -v` passes (all core unit tests green)
7. The full `make check` either passes completely OR the only failures are from files explicitly owned by other sprints (documented)
8. `vulture_whitelist.py` contains only justified suppressions (no stale references)

## Verification / quality gates

- [ ] All core unit tests pass
- [ ] Linters/formatters pass for all sprint-owned files
- [ ] vulture clean for sprint-owned files
- [ ] jscpd clean
- [ ] No new warnings introduced
- [ ] Known external failures documented

## Edge cases

- `nl_processing/extract_text_from_image/__init__.py` is still non-empty — ruff will flag it with `RUF029`. This is owned by the extract_text_from_image sprint. Document as known issue.
- `tests/unit/extract_text_from_image/test_extract_text_from_image.py` imports from the broken root `__init__.py`. This test will fail. Owned by extract_text_from_image sprint. Document as known issue.
- If `make check` runs integration/e2e tests that require `OPENAI_API_KEY`, use `doppler run -- make check`. If Doppler is not configured yet, run the individual steps that don't need API keys separately.

## Rollout / rollback (if relevant)

- Rollout: Fix issues and update whitelist in a single commit.
- Rollback: Revert the commit.

## Notes / risks

- **Risk**: `make check` may fail on files not owned by this sprint. **Mitigation**: Document these failures explicitly. The sprint's DoD requires core tests to pass and sprint-owned files to be clean — not necessarily a fully green `make check` if other sprints haven't run yet.
- **Known expected failures from other sprints**:
  - `nl_processing/extract_text_from_image/__init__.py` — non-empty (ruff RUF029)
  - `tests/unit/extract_text_from_image/test_extract_text_from_image.py` — broken import from `nl_processing` root
  - These will be fixed by the `module-extract-text-from-image` sprint.
