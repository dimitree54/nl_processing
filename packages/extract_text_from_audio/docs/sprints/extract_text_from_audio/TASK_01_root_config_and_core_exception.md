---
Task ID: `T1`
Title: `Root config updates and UnsupportedAudioFormatError in core`
Sprint: `2026-03-12_extract-text-from-audio`
Module: `extract_text_from_audio`
Depends on: `--`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Register `extract_text_from_audio` in the monorepo build/lint pipeline (Makefile + ruff.toml) and add the `UnsupportedAudioFormatError` exception to `core`, so that all subsequent tasks can run `make check` and import the shared exception.

## Context (contract mapping)

- Requirements: `packages/extract_text_from_audio/docs/module-spec.md` — IF-3 (shared helpers from core), FM-1 (UnsupportedAudioFormatError)
- Reference pattern: `packages/core/src/nl_processing/core/exceptions.py` — existing `UnsupportedImageFormatError`
- Root config: `Makefile` line 1 (PACKAGES list), `ruff.toml` lines 4-14 (src list)

## Preconditions

- Root `Makefile` currently lists `PACKAGES = core extract_text_from_image extract_words_from_text translate_text translate_text_from_image translate_word database database_cache sampling` (does NOT include `extract_text_from_audio`).
- Root `ruff.toml` src list does NOT include `packages/extract_text_from_audio/src`.
- `core/exceptions.py` has `UnsupportedImageFormatError` but NOT `UnsupportedAudioFormatError`.

## Non-goals

- WAV validator implementation (T2)
- Realtime runner implementation (T3)
- Service implementation (T4)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `Makefile` (root) — add package to PACKAGES list
- `ruff.toml` (root) — add src path
- `packages/core/src/nl_processing/core/exceptions.py` — add new exception class
- `packages/extract_text_from_audio/src/nl_processing/extract_text_from_audio/__init__.py` — make strictly empty
- `packages/extract_text_from_audio/tests/` — verify empty init files are strictly empty

**FORBIDDEN — this task must NEVER touch:**
- Any other module's code or tests
- Any other file in `core/`
- Bot code

**Test scope:**
- After changes, run `make check` from `packages/extract_text_from_audio/` to verify the package is registered and lintable.
- The package has no real source or tests yet, so `make check` should pass with empty test suite (0 tests collected is OK for this task).

## Touched surface (expected files / modules)

- `/Users/yid/source/nl_processing/Makefile`
- `/Users/yid/source/nl_processing/ruff.toml`
- `/Users/yid/source/nl_processing/packages/core/src/nl_processing/core/exceptions.py`
- `/Users/yid/source/nl_processing/packages/extract_text_from_audio/src/nl_processing/extract_text_from_audio/__init__.py`

## Dependencies and sequencing notes

- No dependencies. This is the foundation task.
- Must complete before T2, T3, T4 since they all need `make check` to work and/or import `UnsupportedAudioFormatError`.

## Third-party / library research (mandatory for any external dependency)

No third-party libraries introduced in this task.

## Implementation steps (developer-facing)

1. **Update root `Makefile`**: Add `extract_text_from_audio` to the `PACKAGES` variable on line 1. Insert it after `extract_text_from_image` to maintain alphabetical grouping of extract modules. The result should be:
   ```
   PACKAGES = core extract_text_from_image extract_text_from_audio extract_words_from_text translate_text translate_text_from_image translate_word database database_cache sampling
   ```

2. **Update root `ruff.toml`**: Add `"packages/extract_text_from_audio/src"` to the `src` list. Insert it after `"packages/extract_text_from_image/src"`:
   ```toml
   src = [
       "packages/core/src",
       "packages/extract_text_from_image/src",
       "packages/extract_text_from_audio/src",
       "packages/extract_words_from_text/src",
       ...
   ]
   ```

3. **Add `UnsupportedAudioFormatError` to `core/exceptions.py`**: Add a new exception class following the exact pattern of `UnsupportedImageFormatError`:
   ```python
   class UnsupportedAudioFormatError(Exception):
       """Raised when the audio format is not supported."""
   ```

4. **Make `__init__.py` strictly empty**: The current `__init__.py` at `packages/extract_text_from_audio/src/nl_processing/extract_text_from_audio/__init__.py` contains `"""Planned audio extraction package."""`. This must be emptied to comply with `strictly-empty-init-modules = true` in ruff.toml. Make it a completely empty file (0 bytes or just a newline).

5. **Verify all test `__init__.py` files are strictly empty**: Check `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`, `tests/e2e/__init__.py` — all must be empty.

6. **Run `make check`** from `packages/extract_text_from_audio/` to verify:
   - `ruff format` passes
   - `ruff check` passes
   - `pylint` passes (no files over 200 lines)
   - `pytest` runs (0 tests collected is acceptable at this stage)

## Production safety constraints (mandatory)

- **Database operations**: None.
- **Resource isolation**: Only modifying build/lint config files and adding a new exception class. No runtime resources affected.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Extending the existing `exceptions.py` pattern.
- **Correct libraries only**: No new dependencies.
- **Correct file locations**: Following established monorepo layout.
- **No regressions**: Adding to PACKAGES list and src list is additive; existing packages are not affected.

## Error handling + correctness rules (mandatory)

- The new exception class follows the exact pattern of `UnsupportedImageFormatError` — a simple subclass of `Exception` with a docstring. No error silencing.

## Zero legacy tolerance rule (mandatory)

- Remove the docstring from `__init__.py` (it is legacy placeholder content).

## Acceptance criteria (testable)

1. `extract_text_from_audio` appears in root `Makefile` PACKAGES list.
2. `packages/extract_text_from_audio/src` appears in root `ruff.toml` src list.
3. `UnsupportedAudioFormatError` is importable from `nl_processing.core.exceptions`.
4. `__init__.py` at `packages/extract_text_from_audio/src/nl_processing/extract_text_from_audio/__init__.py` is strictly empty.
5. `make check` passes from `packages/extract_text_from_audio/`.

## Verification / quality gates

- [ ] `UnsupportedAudioFormatError` exists in `core/exceptions.py`
- [ ] Root Makefile includes `extract_text_from_audio` in PACKAGES
- [ ] Root ruff.toml includes `packages/extract_text_from_audio/src` in src
- [ ] `__init__.py` is strictly empty
- [ ] `make check` passes from `packages/extract_text_from_audio/`
- [ ] No other modules' files were modified

## Edge cases

- Ensure the PACKAGES ordering doesn't break `make check` for other packages (it shouldn't — packages are processed independently).

## Notes / risks

- Low-risk task: purely additive configuration changes and one new exception class.
