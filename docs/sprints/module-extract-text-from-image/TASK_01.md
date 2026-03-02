---
Task ID: `T1`
Title: `Clean up broken files and add opencv-python dependency`
Sprint: `2026-03-02_module-extract-text-from-image`
Module: `extract_text_from_image`
Depends on: `—`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Clean up the broken legacy files in the `extract_text_from_image` module scope: empty the non-compliant `__init__.py` (currently re-exports the mock function), delete the broken unit test (imports from the now-empty root `__init__.py`), and add `opencv-python` as a project dependency. After this task, the module directory is a clean slate ready for implementation, and OpenCV is available for image handling.

## Context (contract mapping)

- Requirements: `nl_processing/extract_text_from_image/docs/prd_extract_text_from_image.md` — NFR4 (`opencv-python` dependency)
- Architecture: `docs/planning-artifacts/architecture.md` — "Empty `__init__.py` files (enforced by ruff `strictly-empty-init-modules`)", "Module Public Interface Pattern" (callers import directly from `service.py`)
- Architecture: `nl_processing/extract_text_from_image/docs/architecture_extract_text_from_image.md` — module structure
- Related: `ruff.toml` line 77 (`strictly-empty-init-modules = true`)

## Preconditions

- Module-core sprint is complete — `nl_processing/__init__.py` is already empty, core package exists
- Repository has the existing broken files:
  - `nl_processing/extract_text_from_image/__init__.py` — contains `from nl_processing.extract_text_from_image.service import extract_text_from_image`
  - `nl_processing/extract_text_from_image/service.py` — contains mock function (will be replaced in T2)
  - `tests/unit/extract_text_from_image/test_extract_text_from_image.py` — imports `extract_text_from_image` from `nl_processing` root (broken)

## Non-goals

- No implementation of `ImageTextExtractor` — that is T2
- No rewriting of `service.py` yet — that is T2 (leave the mock for now or leave it; T2 will overwrite it)
- No prompt creation — that is T2

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/extract_text_from_image/__init__.py` — make empty (delete all content)
- `tests/unit/extract_text_from_image/test_extract_text_from_image.py` — delete (broken, will be recreated in T5)
- `pyproject.toml` — add `opencv-python` dependency

**FORBIDDEN — this task must NEVER touch:**
- `nl_processing/core/` (owned by module-core sprint)
- `nl_processing/__init__.py` (owned by module-core sprint)
- `nl_processing/extract_words_from_text/`, `nl_processing/translate_text/`, `nl_processing/translate_word/`, `nl_processing/database/`
- `nl_processing/extract_text_from_image/service.py` — not yet (T2 will rewrite it)
- Any docs outside `docs/sprints/module-extract-text-from-image/`
- `Makefile`, `ruff.toml`, `pytest.ini`

**Test scope:**
- After this task, there are no tests to run for this module (old test deleted, new tests not yet created)
- Verify: `uv run ruff check nl_processing/extract_text_from_image/__init__.py` — no violations
- Verify: `uv sync --all-groups` — opencv installed

## Touched surface (expected files / modules)

- `nl_processing/extract_text_from_image/__init__.py` — emptied
- `tests/unit/extract_text_from_image/test_extract_text_from_image.py` — deleted
- `pyproject.toml` — `opencv-python` added

## Dependencies and sequencing notes

- This is the first task — no dependencies within this sprint
- Depends on module-core sprint being complete (so `nl_processing/__init__.py` is already empty)
- Must run before T2 because T2 needs a clean `__init__.py` and opencv installed

## Third-party / library research (mandatory for any external dependency)

- **Library**: `opencv-python` — version range `>=4.10,<5`
  - **Official documentation**: https://docs.opencv.org/4.x/
  - **PyPI**: https://pypi.org/project/opencv-python/
  - **Python API reference**: https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html
  - **Usage — read image**:
    ```python
    import cv2
    image = cv2.imread("image.png")  # Returns numpy.ndarray
    ```
  - **Usage — encode to bytes**:
    ```python
    import cv2
    success, buffer = cv2.imencode(".png", image)
    image_bytes = buffer.tobytes()
    ```
  - **Usage — create synthetic image**:
    ```python
    import numpy
    import cv2
    img = numpy.zeros((100, 400, 3), dtype=numpy.uint8)
    img.fill(255)  # white background
    cv2.putText(img, "Hello", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    ```
  - **Known gotchas**:
    - `opencv-python` installs `numpy` as a dependency — no separate numpy dependency needed.
    - `opencv-python` vs `opencv-python-headless`: Use `opencv-python` (full) since we need `putText` for synthetic images. Both provide the same Python API; the headless variant just lacks GUI functions. Either works for our use case, but `opencv-python` is the standard.
    - Pre-built wheels available for macOS, Linux, Windows on Python 3.12+.

## Implementation steps (developer-facing)

1. **Empty `nl_processing/extract_text_from_image/__init__.py`**: Replace the entire file content with an empty file (zero bytes or just a newline). Current content (`from nl_processing.extract_text_from_image.service import extract_text_from_image`) violates ruff `strictly-empty-init-modules`.

2. **Delete `tests/unit/extract_text_from_image/test_extract_text_from_image.py`**: This file imports `extract_text_from_image` from the `nl_processing` root (which no longer re-exports anything). It tests the mock function which is being replaced. Delete it entirely. New tests will be created in T5.
   - Keep `tests/unit/extract_text_from_image/__init__.py` — it is needed for the test directory structure.

3. **Add `opencv-python` to `pyproject.toml`**: In the `[project] dependencies` list, add `"opencv-python>=4.10,<5"`.

4. **Run `uv sync --all-groups`** to install opencv-python.

5. **Verify**:
   ```bash
   uv run ruff check nl_processing/extract_text_from_image/__init__.py
   # Should produce no errors

   uv run python -c "import cv2; print(cv2.__version__)"
   # Should print the installed opencv version

   uv run python -c "import numpy; print(numpy.__version__)"
   # Should work (numpy installed as opencv dependency)
   ```

## Production safety constraints (mandatory)

- **Database operations**: None.
- **Resource isolation**: Adding a dependency and cleaning files does not affect the production instance (different directory, different virtualenv).
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Using the standard `opencv-python` package — no custom alternatives.
- **Correct libraries only**: `opencv-python>=4.10,<5` — current stable release line. Version chosen to ensure Python 3.12+ compatibility and stable API.
- **Correct file locations**: Only modifying files within the ALLOWED list.
- **No regressions**: The deleted test was already broken (import error). Emptying `__init__.py` removes the ruff violation. Adding opencv does not break anything.

## Error handling + correctness rules (mandatory)

- N/A — this task modifies metadata and removes broken code; no error handling code is written.

## Zero legacy tolerance rule (mandatory)

After this task:
- `nl_processing/extract_text_from_image/__init__.py` is empty — no re-exports, compliant with ruff
- The broken test file is removed — no stale test code referencing deleted imports
- The mock `service.py` still exists but will be replaced in T2 — this is acceptable as an intermediate state

## Acceptance criteria (testable)

1. `nl_processing/extract_text_from_image/__init__.py` is empty (0 lines of code)
2. `tests/unit/extract_text_from_image/test_extract_text_from_image.py` does not exist
3. `tests/unit/extract_text_from_image/__init__.py` still exists (directory intact)
4. `pyproject.toml` contains `"opencv-python>=4.10,<5"` in `[project] dependencies`
5. `uv sync --all-groups` completes without errors
6. `uv run python -c "import cv2"` succeeds
7. `uv run ruff check nl_processing/extract_text_from_image/__init__.py` produces no errors

## Verification / quality gates

- [x] Linters pass for touched files
- [x] No new warnings introduced
- [x] Zero legacy tolerance: broken test removed, `__init__.py` emptied

## Edge cases

- `tests/unit/extract_text_from_image/__init__.py` must NOT be deleted — only the test file is deleted. The directory and its `__init__.py` remain for future tests.
- If `opencv-python` conflicts with other dependencies during `uv sync`, check the version range. The broad `>=4.10,<5` range should avoid conflicts.

## Rollout / rollback (if relevant)

- Rollout: Apply all changes in a single commit.
- Rollback: `git checkout -- <files>` to restore previous state.

## Notes / risks

- **Risk**: None significant. This is a cleanup task with a dependency addition.
