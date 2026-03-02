---
Task ID: `T7`
Title: `Final verification: make check passes`
Sprint: `2026-03-02_module-extract-text-from-image`
Module: `extract_text_from_image`
Depends on: `T5, T6`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Run the full `make check` pipeline and fix any remaining issues so that the quality gate passes for the `extract_text_from_image` module. This is the sprint's Definition of Done gate — after this task, ruff, pylint, vulture, jscpd, and all module tests (unit, integration, e2e) pass cleanly. Update `vulture_whitelist.py` if needed for false positives from the new module code.

## Context (contract mapping)

- Requirements: `docs/planning-artifacts/prd.md` — SNFR5 (100% test pass rate)
- Architecture: `docs/planning-artifacts/architecture.md` — "Quality Gate: `make check`"
- Related: `Makefile` — defines the full `make check` pipeline

## Preconditions

- T1 through T6 all completed
- All module source files exist: `service.py`, `image_encoding.py`, `benchmark.py`, `prompts/nl.json`
- All test files exist: unit, integration, and e2e tests
- Module-core sprint complete (no broken core files)

## Non-goals

- No new feature implementation — only fixes to pass `make check`
- No changes to `Makefile`, `ruff.toml`, or `pytest.ini`
- No fixing issues in other modules' files

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `vulture_whitelist.py` (modify — add false-positive suppressions if needed)
- Any file in the ALLOWED list from the SPRINT.md — but only to fix issues discovered during `make check`
- Specifically: `nl_processing/extract_text_from_image/`, `tests/unit/extract_text_from_image/`, `tests/integration/extract_text_from_image/`, `tests/e2e/extract_text_from_image/`

**FORBIDDEN — this task must NEVER touch:**
- `nl_processing/core/` (owned by module-core sprint)
- Any other module's code or tests
- `Makefile`, `ruff.toml`, `pytest.ini`
- Any docs outside `docs/sprints/module-extract-text-from-image/`
- Requirements/architecture docs

**Test scope:**
- Run the full `make check` pipeline (includes all modules)
- Module-specific: `doppler run -- uv run pytest tests/unit/extract_text_from_image/ tests/integration/extract_text_from_image/ tests/e2e/extract_text_from_image/ -x -v`

## Touched surface (expected files / modules)

- `vulture_whitelist.py` — may need updates for false positives
- Possibly minor fixes to module files if `make check` reveals issues

## Dependencies and sequencing notes

- Depends on all previous tasks (T1-T6)
- This is the final task — no other task depends on it
- Must run sequentially after all other tasks complete

## Third-party / library research (mandatory for any external dependency)

N/A — this task uses only existing tools.

## Implementation steps (developer-facing)

1. **Run module-specific tests first** (faster feedback):
   ```bash
   uv run pytest tests/unit/extract_text_from_image/ -x -v
   doppler run -- uv run pytest tests/integration/extract_text_from_image/ -x -v
   doppler run -- uv run pytest tests/e2e/extract_text_from_image/ -x -v
   ```

2. **Run linting on module files**:
   ```bash
   uv run ruff format nl_processing/extract_text_from_image/ tests/unit/extract_text_from_image/ tests/integration/extract_text_from_image/ tests/e2e/extract_text_from_image/
   uv run ruff check nl_processing/extract_text_from_image/ tests/unit/extract_text_from_image/ tests/integration/extract_text_from_image/ tests/e2e/extract_text_from_image/
   ```

3. **Run pylint 200-line check on module**:
   ```bash
   uvx pylint nl_processing/extract_text_from_image/ tests/unit/extract_text_from_image/ tests/integration/extract_text_from_image/ tests/e2e/extract_text_from_image/ --disable=all --enable=C0302 --max-module-lines=200
   ```

4. **Run vulture**:
   ```bash
   uv run vulture nl_processing tests vulture_whitelist.py
   ```
   If vulture flags functions in `benchmark.py` (e.g., `run_benchmark`, `generate_test_image`) as unused, add them to `vulture_whitelist.py`:
   ```python
   from nl_processing.extract_text_from_image.benchmark import (
       generate_test_image,
       normalize_text,
       evaluate_extraction,
       run_benchmark,
   )
   ```

5. **Run jscpd**:
   ```bash
   npx jscpd --exitCode 1
   ```
   If code duplication is detected between test files, refactor to extract shared fixtures.

6. **Run full `make check`**:
   ```bash
   doppler run -- make check
   ```

7. **Analyze any failures** — categorize each failure as:
   - (a) Owned by this sprint → fix it
   - (b) Owned by another sprint → document but do not fix
   - (c) Pre-existing issue → document but do not fix

8. **Fix owned failures** and re-run until clean.

9. **Verify the public interface** matches the architecture spec:
   ```bash
   uv run python -c "
   from nl_processing.extract_text_from_image.service import ImageTextExtractor
   from nl_processing.core.models import Language
   e = ImageTextExtractor  # class exists
   assert hasattr(e, 'extract_from_path')
   assert hasattr(e, 'extract_from_cv2')
   print('Interface verified')
   "
   ```

## Production safety constraints (mandatory)

- **Database operations**: None.
- **Resource isolation**: Tests use Doppler dev environment. No production resources accessed.
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
- The mock `service.py` should be completely gone — replaced by `ImageTextExtractor`.
- The old `__init__.py` re-exports should be gone — file is empty.
- The old broken test should be gone — replaced by new tests.

## Acceptance criteria (testable)

1. `uv run ruff format` produces no changes in sprint-owned files
2. `uv run ruff check` produces no errors in sprint-owned files
3. `uvx pylint nl_processing/extract_text_from_image/ --disable=all --enable=C0302 --max-module-lines=200` passes (all files ≤200 lines)
4. `uv run vulture nl_processing tests vulture_whitelist.py` produces no errors in sprint-owned files
5. `npx jscpd --exitCode 1` passes
6. `uv run pytest tests/unit/extract_text_from_image/ -x -v` passes
7. `doppler run -- uv run pytest tests/integration/extract_text_from_image/ -x -v` passes
8. `doppler run -- uv run pytest tests/e2e/extract_text_from_image/ -x -v` passes
9. `doppler run -- make check` either passes completely OR the only failures are from files owned by other sprints (documented)
10. `nl_processing/extract_text_from_image/__init__.py` is empty
11. No reference to old mock function `extract_text_from_image` exists in any sprint-owned file
12. Public interface matches architecture: `ImageTextExtractor` with `extract_from_path` and `extract_from_cv2`

## Verification / quality gates

- [ ] All module tests pass (unit, integration, e2e)
- [ ] Linters/formatters pass
- [ ] vulture clean
- [ ] jscpd clean
- [ ] pylint 200-line check passes
- [ ] Public interface verified against architecture spec
- [ ] Zero legacy: old mock removed, old test removed, `__init__.py` empty

## Edge cases

- If `make check` runs integration/e2e tests without `doppler run --`, they will fail due to missing `OPENAI_API_KEY`. Use `doppler run -- make check`.
- If `vulture` flags benchmark functions as unused, whitelist them (they are used by integration tests at runtime, but vulture does static analysis and may miss the usage).
- If `jscpd` flags test files for duplication (similar assertion patterns), refactor test helpers or accept if the duplication is minimal and intentional for readability.

## Rollout / rollback (if relevant)

- Rollout: Fix issues and update whitelist in a single commit.
- Rollback: Revert the commit.

## Notes / risks

- **Risk**: `make check` may fail on files not owned by this sprint (e.g., other modules still have mock service.py files). **Mitigation**: Document these as expected failures from future sprints.
- **Risk**: Integration tests may be flaky due to API network variability. **Mitigation**: Re-run failures once before investigating code changes. Keep test suite small.
- **Expected external issues** (owned by future sprints):
  - `nl_processing/extract_words_from_text/service.py`, `nl_processing/translate_text/service.py`, `nl_processing/translate_word/service.py` — still contain mock implementations
  - Other modules' test directories may have broken or missing tests
