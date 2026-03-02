---
Task ID: `T1`
Title: `Legacy cleanup: empty all __init__.py files, remove dead tests, update vulture whitelist`
Sprint: `2026-03-02_module-core`
Module: `core`
Depends on: `—`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Eliminate all broken imports and dead code that prevent `make check` from passing. After this task, the project has no references to the non-existent `nl_processing.processor` module, all `__init__.py` files comply with ruff's `strictly-empty-init-modules` rule, dead test files are removed, and `vulture_whitelist.py` is updated. This unblocks all subsequent tasks.

## Context (contract mapping)

- Requirements: `docs/planning-artifacts/prd.md` — SFR12-14 (documentation conventions), SNFR5 (100% test pass rate)
- Architecture: `docs/planning-artifacts/architecture.md` — "Empty `__init__.py` files (enforced by ruff `strictly-empty-init-modules`)", "Module Public Interface Pattern" (callers import directly from `service.py`, no `__init__.py` re-export), "Zero-legacy policy"
- Related: `ruff.toml` line 77 (`strictly-empty-init-modules = true`)

## Preconditions

- Repository checked out with current broken state
- `uv sync --all-groups` has been run (dev dependencies installed)

## Non-goals

- No new code is written in this task — only cleanup
- No modification of module `service.py` files — those are owned by their respective sprints
- No creation of `nl_processing/core/` directory — that's T3+

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/__init__.py` — make empty (delete all content)
- `nl_processing/extract_words_from_text/__init__.py` — make empty
- `nl_processing/translate_text/__init__.py` — make empty
- `nl_processing/translate_word/__init__.py` — make empty
- `nl_processing/database/__init__.py` — make empty
- `tests/unit/test_processor_unit.py` — delete entirely
- `tests/unit/database/test_database.py` — delete entirely
- `tests/unit/database/__init__.py` — delete entirely (remove the empty dir)
- `tests/integration/test_processor_integration.py` — delete entirely
- `tests/e2e/test_smoke_e2e.py` — delete entirely
- `tests/e2e/conftest.py` — delete entirely
- `vulture_whitelist.py` — rewrite (remove stale reference to deleted conftest)

**FORBIDDEN — this task must NEVER touch:**
- `nl_processing/extract_text_from_image/__init__.py` — owned by module-extract-text-from-image sprint
- `nl_processing/extract_text_from_image/service.py` — owned by module-extract-text-from-image sprint
- `tests/unit/extract_text_from_image/` — owned by module-extract-text-from-image sprint
- Any module `service.py` file
- Any docs outside `docs/sprints/module-core/`
- `pyproject.toml`, `Makefile`, `ruff.toml`, `pytest.ini`

**Test scope:**
- After this task, run: `uv run ruff check nl_processing/ --select RUF029` (verify no init violations)
- Then run: `uv run ruff check` (verify linting passes across the board)
- Then run: `uv run vulture nl_processing tests vulture_whitelist.py` (verify no dead code)
- Note: `make check` will NOT fully pass yet (no core tests exist yet, and `nl_processing/extract_text_from_image/__init__.py` is still non-empty — owned by another sprint). But the specific files this task touches must not cause failures.
- **Partial verification**: `uv run ruff format && uv run ruff check --fix` should pass without errors related to the cleaned files.

## Touched surface (expected files / modules)

- `nl_processing/__init__.py` — emptied
- `nl_processing/extract_words_from_text/__init__.py` — emptied
- `nl_processing/translate_text/__init__.py` — emptied
- `nl_processing/translate_word/__init__.py` — emptied
- `nl_processing/database/__init__.py` — emptied
- `tests/unit/test_processor_unit.py` — deleted
- `tests/unit/database/` — entire directory deleted
- `tests/integration/test_processor_integration.py` — deleted
- `tests/e2e/test_smoke_e2e.py` — deleted
- `tests/e2e/conftest.py` — deleted
- `vulture_whitelist.py` — rewritten

## Dependencies and sequencing notes

- This is the first task — no dependencies
- Must run before all other tasks because broken imports block `make check`
- Must run before T2 (dependency changes) because current broken state prevents testing

## Third-party / library research (mandatory for any external dependency)

N/A — this task does not introduce or use any third-party libraries.

## Implementation steps (developer-facing)

1. **Empty `nl_processing/__init__.py`**: Replace the entire file content with an empty file (zero bytes or just a newline). The current file imports from `nl_processing.processor` which does not exist and from module `__init__.py` files that re-export — all of this violates `strictly-empty-init-modules`.

2. **Empty `nl_processing/extract_words_from_text/__init__.py`**: Replace content with empty file. Current file re-exports `extract_words_from_text` from `service.py`.

3. **Empty `nl_processing/translate_text/__init__.py`**: Replace content with empty file. Current file re-exports `translate_text` from `service.py`.

4. **Empty `nl_processing/translate_word/__init__.py`**: Replace content with empty file. Current file re-exports `translate_word` from `service.py`.

5. **Empty `nl_processing/database/__init__.py`**: Replace content with empty file. Current file re-exports `save_translation` from `service.py`.

6. **Delete `tests/unit/test_processor_unit.py`**: This file imports `normalize_text` from `nl_processing` (which came from the non-existent `nl_processing.processor`). The `processor` module does not exist in the architecture — this is dead code.

7. **Delete `tests/unit/database/test_database.py`**: This file imports `save_translation` from `nl_processing` root (via the now-emptied `__init__.py`). The `database` module is out of scope for this architecture. Delete the file.

8. **Delete `tests/unit/database/__init__.py`**: Remove the now-empty test directory's init file.

9. **Remove the `tests/unit/database/` directory**: Clean up the empty directory.

10. **Delete `tests/integration/test_processor_integration.py`**: This file imports `MockPayload` and `normalize_text` from the non-existent `nl_processing.processor`. Dead code.

11. **Delete `tests/e2e/test_smoke_e2e.py`**: This file tests e2e options for the old processor flow. No longer relevant.

12. **Delete `tests/e2e/conftest.py`**: This file defines `pytest_addoption` for the `--e2e-client` option used only by the deleted `test_smoke_e2e.py`. No other test uses this option.

13. **Rewrite `vulture_whitelist.py`**: The current content references `tests.e2e.conftest.pytest_addoption` which no longer exists. Replace with an empty whitelist (just a comment explaining the file's purpose) or a minimal valid Python file. Example:
    ```python
    # Vulture whitelist — list false-positive "unused" symbols here.
    ```

14. **Verify**: Run `uv run ruff format && uv run ruff check --fix` — confirm no errors from cleaned files.

15. **Verify**: Run `uv run vulture nl_processing tests vulture_whitelist.py` — confirm no dead code errors from deleted files.

## Production safety constraints (mandatory)

- **Database operations**: None — this task only deletes/empties files.
- **Resource isolation**: No shared resources affected. File deletions are within the dev workspace only.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: N/A — this is cleanup only.
- **Correct libraries only**: N/A.
- **Correct file locations**: All file operations target the exact files listed in ALLOWED.
- **No regressions**: The files being deleted are already broken (they import from non-existent modules). Deleting them removes failures, not introduces them.
- **Follow UX/spec**: N/A.

## Error handling + correctness rules (mandatory)

- N/A — no error handling code is written in this task (cleanup only).

## Zero legacy tolerance rule (mandatory)

After this task:
- All references to the non-existent `nl_processing.processor` module are removed
- All `__init__.py` files touched by this task are empty (compliant with ruff `strictly-empty-init-modules`)
- All dead test files are removed — no stubs, no "TODO" placeholders
- `vulture_whitelist.py` contains no stale references

## Acceptance criteria (testable)

1. `nl_processing/__init__.py` is empty (0 lines of code)
2. `nl_processing/extract_words_from_text/__init__.py` is empty
3. `nl_processing/translate_text/__init__.py` is empty
4. `nl_processing/translate_word/__init__.py` is empty
5. `nl_processing/database/__init__.py` is empty
6. `tests/unit/test_processor_unit.py` does not exist
7. `tests/unit/database/` directory does not exist
8. `tests/integration/test_processor_integration.py` does not exist
9. `tests/e2e/test_smoke_e2e.py` does not exist
10. `tests/e2e/conftest.py` does not exist
11. `vulture_whitelist.py` contains no reference to `pytest_addoption` or `tests.e2e.conftest`
12. `uv run ruff format` produces no errors
13. `uv run ruff check` produces no errors related to the cleaned files
14. `uv run vulture nl_processing tests vulture_whitelist.py` produces no errors from deleted/cleaned files

## Verification / quality gates

- [x] Linters/formatters pass for touched files
- [x] No new warnings introduced
- [x] Zero legacy tolerance: all dead code removed, all broken imports eliminated

## Edge cases

- `nl_processing/extract_text_from_image/__init__.py` is also non-empty but is NOT touched in this task — it is owned by the extract_text_from_image sprint. Ruff may still flag it. This is expected and will be fixed in that sprint.
- `tests/unit/extract_text_from_image/test_extract_text_from_image.py` imports from the broken `nl_processing` root. This file is NOT touched here — owned by the extract_text_from_image sprint. It will fail if run. This is expected.

## Rollout / rollback (if relevant)

- Rollout: Apply all file changes in a single commit.
- Rollback: `git checkout -- <list of files>` to restore previous state.

## Notes / risks

- **Risk**: After emptying `__init__.py` files, `tests/unit/extract_text_from_image/test_extract_text_from_image.py` will fail because it imports `extract_text_from_image` from `nl_processing` root. This file is owned by the extract_text_from_image sprint and will be rewritten there. **Mitigation**: This task's verification does NOT require `make check` to fully pass — only that the files this task touches are clean. The full `make check` pass is the DoD for the overall sprint (T7).
- **Risk**: `tests/unit/database/__init__.py` deletion leaves the `tests/unit/database/` directory. **Mitigation**: Explicitly remove the directory in step 9.
