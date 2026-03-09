---
Task ID: T8
Title: Final integration — vulture whitelist, full `make check` validation
Sprint: `translate_text_from_image`
Module: `translate_text_from_image` (+ root config)
Depends on: T7
Parallelizable: no
Owner: Developer
Status: planned
---

## Goal / value

Register the new module's public API in the vulture dead-code whitelist and validate that the entire monorepo passes `make check` — including jscpd copy-paste detection, vulture dead-code analysis, linting, and all package tests across the repo.

## Context (contract mapping)

- Module spec: `packages/translate_text_from_image/docs/module-spec.md` — SC-1
- Build system: root `Makefile` (`make check`), `vulture_whitelist.py`, `.jscpd.json`

## Preconditions

- T1–T7 all completed. The new package has service, prompt, and all tests passing.
- `extract_text_from_image` updated to import from core (T1).
- `build_translation_chain` extended (T2).
- Root Makefile and ruff.toml updated (T3).

## Non-goals

- Code changes to fix issues (any issues found should be fixed in the appropriate earlier task's scope and re-validated).
- New features or tests beyond what's needed for `make check` to pass.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `vulture_whitelist.py` (root) — add new module's public API entries

**FORBIDDEN — this task must NEVER touch:**
- Any package source code (if something fails, go back and fix in the relevant task)
- Any test files
- Any other root config files (already handled in T3)

**Test scope:**
- Test command: `make check` (root — runs all packages)
- This is the ONLY task in the sprint that runs the full repo check.

## Touched surface (expected files / modules)

- `vulture_whitelist.py` (root) — modified

## Dependencies and sequencing notes

- Depends on all previous tasks. This is the final validation step.
- No tasks depend on this.

## Implementation steps

### Step 1: Update `vulture_whitelist.py`

Add entries for the new module's public API that vulture will flag as "unused" (since no consumer exists yet in the repo):

```python
# translate_text_from_image — public API, consumed by future callers
from nl_processing.translate_text_from_image.service import ImageTextTranslator
ImageTextTranslator.translate_from_path  # type: ignore[misc]
ImageTextTranslator.translate_from_cv2  # type: ignore[misc]
```

Also add the benchmark utility if it exists:
```python
from nl_processing.translate_text_from_image.benchmark import render_text_image
```

Also add to the `__all__` list at the bottom of the file.

Check if any image encoding functions from core need whitelisting (they are used by the new module, so they should NOT be flagged). If the re-exports in `extract_text_from_image/image_encoding.py` cause vulture to flag the `__all__` variable, add it.

### Step 2: Run `make check` (full repo)

```bash
make check
```

This runs:
1. `vulture` across all packages — verifies no dead code (with whitelist).
2. `jscpd` across all packages — verifies no duplicated 10+ line blocks.
3. Per-package `make check` for every package in PACKAGES list.

### Step 3: Fix any failures

If `make check` reveals issues:

- **jscpd failures**: Identify the duplicated blocks. If they're in the new package's source code or tests (not conftest.py), go back to the relevant task and refactor. Do NOT suppress jscpd.
- **vulture failures**: Add missing whitelist entries in this task.
- **lint failures**: Should have been caught by per-package checks. If new, fix in the relevant package.
- **test failures in other packages**: If T1 (image helper promotion) broke `extract_text_from_image` tests, go back to T1 and fix.
- **test failures in new package**: Go back to the relevant task (T4/T6/T7) and fix.

### Step 4: Final verification

After all issues are resolved:
```bash
make check
```
Must exit 0 with no errors or warnings.

## Production safety constraints

- No database operations.
- `make check` runs tests for all packages (some with live API via doppler).
- No production resources affected — all tests use testing credentials.

## Anti-disaster constraints

- **No regressions**: Full repo check ensures nothing is broken.
- **Correct file locations**: Only `vulture_whitelist.py` is modified.

## Error handling + correctness rules

- N/A — this task is pure validation and whitelist configuration.

## Zero legacy tolerance rule

- Verify there is no dead code in the new package.
- Verify `extract_text_from_image/image_encoding.py` is a clean re-export (no dead logic).

## Acceptance criteria (testable)

1. `vulture_whitelist.py` includes `ImageTextTranslator` and its public methods.
2. `make check` passes with exit code 0.
3. No jscpd violations.
4. No vulture violations.
5. All package tests pass (core, extract_text_from_image, translate_text, translate_text_from_image, and all others).

## Verification / quality gates

- [x] Full `make check` passes
- [x] jscpd: 0 duplicates across entire repo
- [x] vulture: 0 dead code (with whitelist)
- [x] All linters pass
- [x] All unit tests pass
- [x] All integration tests pass
- [x] All e2e tests pass

## Edge cases

- `vulture_whitelist.py` is approaching its line limit. Currently at 153 lines. Adding ~8 lines keeps it under 200.
- jscpd might flag conftest.py files — but these are in the ignore list (`.jscpd.json`: `packages/*/tests/**/conftest.py`).

## Notes / risks

- **Risk**: jscpd flags unexpected duplication between new and existing code.
  - **Mitigation**: This task is the safety net. If found, the specific duplicated block must be refactored (extract to core, or restructure the code to be unique).
- **Risk**: Other package tests might fail due to unrelated issues (flaky API tests).
  - **Mitigation**: If a failure is clearly unrelated to this sprint's changes (e.g., a flaky test in `database`), document it and report to user. Do not mask the failure.
