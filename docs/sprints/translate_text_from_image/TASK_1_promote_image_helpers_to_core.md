---
Task ID: T1
Title: Promote image encoding helpers from `extract_text_from_image` to `core`
Sprint: `translate_text_from_image`
Module: `core` + `extract_text_from_image` (refactor)
Depends on: --
Parallelizable: yes, with T2
Owner: Developer
Status: planned
---

## Goal / value

Move generic image format validation and base64 encoding helpers into `core` so that `translate_text_from_image` can use them without depending on `extract_text_from_image`. Update `extract_text_from_image` to import from `core` instead, eliminating code duplication.

## Context (contract mapping)

- Module spec: `packages/translate_text_from_image/docs/module-spec.md` — DEC-3, NFR-4, A-3
- Current location: `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/image_encoding.py`
- Target location: `packages/core/src/nl_processing/core/image_encoding.py`

## Preconditions

- `packages/core/` exists and is a working package.
- `packages/extract_text_from_image/` tests pass before this change.

## Non-goals

- Adding new image format support.
- Changing function signatures or behavior.
- Modifying any tests beyond updating import paths.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `packages/core/src/nl_processing/core/image_encoding.py` — NEW file (promoted helpers)
- `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/image_encoding.py` — replace with re-exports from core
- `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/service.py` — update imports
- `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/prompts/generate_nl_prompt.py` — update imports

**FORBIDDEN — this task must NEVER touch:**
- `packages/translate_text/` or any other package
- Test files (imports are via the package's public API which will still re-export)
- `packages/extract_text_from_image/tests/` — the re-exports keep the public API stable

**Test scope:**
- Tests stay in: `packages/extract_text_from_image/tests/`
- Test command: `make -C packages/extract_text_from_image check`

## Touched surface (expected files / modules)

- `packages/core/src/nl_processing/core/image_encoding.py` (new)
- `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/image_encoding.py` (modified)
- `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/service.py` (import update)
- `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/prompts/generate_nl_prompt.py` (import update)

## Dependencies and sequencing notes

- No dependencies. Can run in parallel with T2.
- T3 depends on this task (new package needs image helpers from core).

## Implementation steps

1. **Create `packages/core/src/nl_processing/core/image_encoding.py`** by moving the following functions and constants from `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/image_encoding.py`:
   - `SUPPORTED_EXTENSIONS` constant
   - `get_image_format(path: str) -> str`
   - `validate_image_format(path: str) -> None`
   - `encode_path_to_base64(path: str) -> tuple[str, str]`
   - `encode_cv2_to_base64(image: numpy.ndarray) -> tuple[str, str]`
   - `_suffix_to_media_type(suffix: str) -> str`

   Keep the exact same function signatures, docstrings, and behavior. Keep the same imports (`base64`, `pathlib`, `cv2`, `numpy`, `UnsupportedImageFormatError` from core).

2. **Update `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/image_encoding.py`** to become a thin re-export module:
   ```python
   from nl_processing.core.image_encoding import (
       SUPPORTED_EXTENSIONS,
       encode_cv2_to_base64,
       encode_path_to_base64,
       get_image_format,
       validate_image_format,
   )

   __all__ = [
       "SUPPORTED_EXTENSIONS",
       "encode_cv2_to_base64",
       "encode_path_to_base64",
       "get_image_format",
       "validate_image_format",
   ]
   ```

3. **Update `service.py`** imports: change the image_encoding imports to come from `nl_processing.core.image_encoding` instead of the local module. This removes the indirect dependency.

4. **Update `prompts/generate_nl_prompt.py`** imports: change `encode_path_to_base64` import to come from `nl_processing.core.image_encoding`.

5. **Verify**: Run `make -C packages/extract_text_from_image check` — all unit, integration, and e2e tests must pass unchanged.

6. **Verify file size**: `image_encoding.py` in core should be ~63 lines (same as original). The re-export module in `extract_text_from_image` should be ~12 lines.

## Production safety constraints

- No database operations.
- No shared resource changes.
- This is a pure code move — existing behavior is unchanged.

## Anti-disaster constraints

- **Reuse before build**: This IS the reuse step — moving shared code to core.
- **No regressions**: All existing tests must pass without modification.
- **Correct file locations**: New file goes in `packages/core/src/nl_processing/core/`.

## Error handling + correctness rules

- No error handling changes. Functions preserve their existing raise behavior exactly.
- Do not add try/catch or default values.

## Zero legacy tolerance rule

- After this task, the original implementation code in `extract_text_from_image/image_encoding.py` is replaced with re-exports. No duplicated logic remains.
- The re-export module preserves backward compatibility for any code importing from the old location.

## Acceptance criteria (testable)

1. `packages/core/src/nl_processing/core/image_encoding.py` exists and contains all 5 public functions + 1 constant.
2. `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/image_encoding.py` contains only re-exports from core (no logic duplication).
3. `make -C packages/extract_text_from_image check` passes (all unit + integration + e2e).
4. `service.py` and `generate_nl_prompt.py` in `extract_text_from_image` import from `nl_processing.core.image_encoding`.
5. New `image_encoding.py` in core is under 200 lines.

## Verification / quality gates

- [x] Unit tests pass (via `make -C packages/extract_text_from_image check`)
- [x] Integration/e2e tests pass (via same command)
- [x] Linters/formatters pass
- [x] No new warnings introduced
- [x] jscpd passes (re-export module is under 10 lines of logic, no duplication)

## Edge cases

- Import from old path (`nl_processing.extract_text_from_image.image_encoding`) still works via re-exports.
- `cv2` and `numpy` are dependencies of core's `image_encoding.py` — verify they are in core's `pyproject.toml` dependencies (they may need to be added).

## Notes / risks

- **Risk**: `core` package's `pyproject.toml` may not include `opencv-python` and `numpy` as dependencies since it didn't need them before.
  - **Mitigation**: Check `packages/core/pyproject.toml` and add `numpy>=2.0,<3` and `opencv-python>=4.10,<5` if missing. These are already used transitively, so this is a correct declaration.
- **Risk**: jscpd might flag the re-export file if it looks too similar to imports elsewhere.
  - **Mitigation**: Re-export is a standard `from X import Y` block — under 10 lines, well below jscpd's `minLines: 10` threshold.
