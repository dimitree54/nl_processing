---
Task ID: T3
Title: Create `translate_text_from_image` package scaffolding and root build integration
Sprint: `translate_text_from_image`
Module: `translate_text_from_image`
Depends on: T1, T2
Parallelizable: no
Owner: Developer
Status: planned
---

## Goal / value

Create the full package directory structure for `translate_text_from_image` following the established monorepo conventions, and register the package with the root build system so that `make check` includes it.

## Context (contract mapping)

- Module spec: `packages/translate_text_from_image/docs/module-spec.md`
- Pattern: `packages/extract_text_from_image/` and `packages/translate_text/` — follow their scaffolding exactly
- Build system: root `Makefile` (PACKAGES list), root `ruff.toml` (src list)

## Preconditions

- T1 completed (image helpers available in core).
- T2 completed (extended `build_translation_chain` available in core).

## Non-goals

- Implementing the service logic (T4).
- Creating prompt assets (T5).
- Writing tests beyond the directory structure and `__init__.py` files.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `packages/translate_text_from_image/` — all new scaffolding files
- `Makefile` (root) — add to PACKAGES list
- `ruff.toml` (root) — add src path

**FORBIDDEN — this task must NEVER touch:**
- Any other package's source code or tests
- Any existing package config files

**Test scope:**
- Tests go in: `packages/translate_text_from_image/tests/`
- Test command: `make -C packages/translate_text_from_image check`
- At this point, tests directory will be empty (just `__init__.py` files), so the check verifies linting only.

## Touched surface (expected files / modules)

New files to create:
- `packages/translate_text_from_image/pyproject.toml`
- `packages/translate_text_from_image/Makefile`
- `packages/translate_text_from_image/pytest.ini`
- `packages/translate_text_from_image/ruff.toml`
- `packages/translate_text_from_image/src/nl_processing/__init__.py` (empty, namespace)
- `packages/translate_text_from_image/src/nl_processing/translate_text_from_image/__init__.py` (empty)
- `packages/translate_text_from_image/tests/__init__.py`
- `packages/translate_text_from_image/tests/conftest.py`
- `packages/translate_text_from_image/tests/unit/__init__.py`
- `packages/translate_text_from_image/tests/unit/translate_text_from_image/__init__.py`
- `packages/translate_text_from_image/tests/unit/translate_text_from_image/conftest.py`
- `packages/translate_text_from_image/tests/integration/__init__.py`
- `packages/translate_text_from_image/tests/integration/translate_text_from_image/__init__.py`
- `packages/translate_text_from_image/tests/e2e/__init__.py`
- `packages/translate_text_from_image/tests/e2e/translate_text_from_image/__init__.py`
- `packages/translate_text_from_image/tests/e2e/translate_text_from_image/fixtures/` (empty dir for now)

Modified files:
- `Makefile` (root)
- `ruff.toml` (root)

## Dependencies and sequencing notes

- Depends on T1 and T2 because pyproject.toml will declare `nl-processing-core` as a dependency which must already have the image helpers and extended chain builder.
- T4 and T5 depend on this task.

## Implementation steps

1. **Create `packages/translate_text_from_image/pyproject.toml`** following the `extract_text_from_image` pattern:
   ```toml
   [build-system]
   requires = ["setuptools", "wheel"]
   build-backend = "setuptools.build_meta"

   [project]
   name = "nl-processing-translate-text-from-image"
   version = "1.0.0"
   description = "Image text translation package for nl_processing"
   requires-python = ">=3.12"
   dependencies = [
     "nl-processing-core",
     "langchain-core>=0.3,<1",
     "langchain-openai>=0.3,<1",
     "numpy>=2.0,<3",
     "opencv-python>=4.10,<5",
   ]

   [tool.setuptools.packages.find]
   where = ["src"]
   include = ["nl_processing.translate_text_from_image*"]
   namespaces = true

   [tool.setuptools.package-data]
   "nl_processing.translate_text_from_image.prompts" = ["*.json", "examples/*.jpg", "examples/*.png"]

   [dependency-groups]
   dev = [
     "pytest>=9.0.2,<10",
     "pytest-asyncio>=1.3.0,<2",
     "pytest-xdist>=3.8.0,<4",
     "ruff>=0.15.0,<0.16",
     "pylint>=4.0.4,<5",
     "vulture>=2.14.0,<3",
   ]

   [tool.uv.sources]
   nl-processing-core = { path = "../core" }
   ```

2. **Create `packages/translate_text_from_image/Makefile`**:
   ```makefile
   ROOT_DIR := $(abspath ../..)
   TOOLS_VENV ?= $(shell if [ -x "$(CURDIR)/.venv/bin/pytest" ] && [ -x "$(CURDIR)/.venv/bin/ruff" ] && [ -x "$(CURDIR)/.venv/bin/pylint" ] && [ -x "$(CURDIR)/.venv/bin/vulture" ]; then printf '%s' "$(CURDIR)/.venv"; else printf '%s' "$(ROOT_DIR)/.venv"; fi)

   .PHONY: check

   check:
   	$(MAKE) -C "$(ROOT_DIR)" package-check PKG=translate_text_from_image PACKAGE_PYTHONPATH=src:../core/src TOOLS_VENV="$(TOOLS_VENV)"
   ```

3. **Create `packages/translate_text_from_image/pytest.ini`**:
   ```ini
   [pytest]
   testpaths = tests
   python_files = test_*.py
   python_classes = Test*
   python_functions = test_*
   addopts = -v --tb=short -s --log-cli-level=INFO
   asyncio_default_fixture_loop_scope = function
   ```

4. **Create `packages/translate_text_from_image/ruff.toml`**:
   ```toml
   extend = "../../ruff.toml"
   src = ["src", "tests"]
   ```

5. **Create source directory structure** with empty `__init__.py` files:
   - `src/nl_processing/__init__.py` (empty — namespace package)
   - `src/nl_processing/translate_text_from_image/__init__.py` (empty)

6. **Create test directory structure** with `__init__.py` files:
   - `tests/__init__.py`
   - `tests/conftest.py` — shared test helpers (AsyncChainMock etc.)
   - `tests/unit/__init__.py`
   - `tests/unit/translate_text_from_image/__init__.py`
   - `tests/unit/translate_text_from_image/conftest.py`
   - `tests/integration/__init__.py`
   - `tests/integration/translate_text_from_image/__init__.py`
   - `tests/e2e/__init__.py`
   - `tests/e2e/translate_text_from_image/__init__.py`
   - `tests/e2e/translate_text_from_image/fixtures/` (directory, will hold image fixtures in T5/T7)

7. **Create `tests/conftest.py`** following the established pattern. This file is excluded from jscpd (see `.jscpd.json` ignore list: `packages/*/tests/**/conftest.py`):
   ```python
   """Shared test helpers for async chain mocking across this package."""

   from types import SimpleNamespace


   class AsyncChainMock:
       """Async mock for the LangChain chain."""

       def __init__(self, return_value: SimpleNamespace) -> None:
           self.ainvoke_calls: list[dict[str, list[object]]] = []
           self._return_value = return_value

       async def ainvoke(self, input_dict: dict[str, list[object]]) -> SimpleNamespace:
           self.ainvoke_calls.append(input_dict)
           return self._return_value


   class AsyncChainMockError:
       """Async mock that raises an exception on ainvoke."""

       def __init__(self, exception: Exception) -> None:
           self._exception = exception

       async def ainvoke(self, _input_dict: dict[str, list[object]]) -> SimpleNamespace:
           raise self._exception


   def make_tool_response(args: dict[str, object]) -> SimpleNamespace:
       """Build a fake LLM response with tool_calls matching bind_tools output."""
       resp = SimpleNamespace()
       resp.tool_calls = [{"args": args}]
       return resp
   ```

8. **Create `tests/unit/translate_text_from_image/conftest.py`** following the pattern:
   ```python
   """Test fixtures for translate_text_from_image unit tests."""

   from tests.conftest import (
       AsyncChainMock as _AsyncChainMock,
       AsyncChainMockError as _AsyncChainMockError,
       make_tool_response as _make_response,
   )

   __all__ = ["_AsyncChainMock", "_AsyncChainMockError", "make_tool_response"]


   def make_tool_response(text: str) -> object:
       """Build a fake LLM response with tool_calls for _TranslatedImageText."""
       return _make_response({"text": text})
   ```

9. **Update root `Makefile`**: Add `translate_text_from_image` to the `PACKAGES` list:
   ```makefile
   PACKAGES = core extract_text_from_image extract_words_from_text translate_text translate_text_from_image translate_word database database_cache sampling
   ```

10. **Update root `ruff.toml`**: Add new src path to the `src` array:
    ```toml
    src = [
        "packages/core/src",
        "packages/extract_text_from_image/src",
        "packages/extract_words_from_text/src",
        "packages/translate_text/src",
        "packages/translate_text_from_image/src",
        "packages/translate_word/src",
        "packages/database/src",
        "packages/database_cache/src",
        "packages/sampling/src",
    ]
    ```

11. **Verify**: The scaffolding should pass lint checks even with no source code yet. Run `uv run --directory packages/translate_text_from_image ruff check src tests` to confirm no lint errors on empty files.

## Production safety constraints

- No database operations.
- No shared resources affected.
- Purely additive — new directory and two single-line additions to root config.

## Anti-disaster constraints

- **Correct file locations**: Follow exact same structure as `extract_text_from_image` and `translate_text`.
- **Correct libraries only**: Dependencies match versions from existing packages.
- **No regressions**: Root Makefile and ruff.toml changes are additive.

## Error handling + correctness rules

- N/A for scaffolding — no runtime code yet.

## Zero legacy tolerance rule

- No legacy code involved. Fresh package creation.

## Acceptance criteria (testable)

1. Package directory structure exists at `packages/translate_text_from_image/` with all files listed above.
2. `pyproject.toml` declares correct dependencies including `nl-processing-core`.
3. `Makefile` delegates to root `package-check` with correct `PKG` and `PACKAGE_PYTHONPATH`.
4. Root `Makefile` PACKAGES list includes `translate_text_from_image`.
5. Root `ruff.toml` src list includes `packages/translate_text_from_image/src`.
6. All `__init__.py` files are empty (strictly empty init modules enforced by ruff).
7. `tests/conftest.py` and `tests/unit/translate_text_from_image/conftest.py` exist with mock helpers.
8. Lint passes on the empty package.

## Verification / quality gates

- [x] Linters/formatters pass on new package
- [x] No new warnings introduced
- [x] File structure matches established package patterns
- [x] All files under 200 lines

## Edge cases

- The `src/nl_processing/__init__.py` must exist but be empty for the namespace package to work.
- The `tests/e2e/translate_text_from_image/fixtures/` directory should exist even if empty (needed by T7).

## Notes / risks

- **Risk**: Package check might fail if there are no test files in `tests/unit/`.
  - **Mitigation**: The `package-check` target uses `pytest` which will simply collect 0 tests and pass. Alternatively, create a placeholder `test_placeholder.py` that can be removed in T4. But checking the Makefile — pytest with `-n auto` on an empty directory exits 0 if `testpaths = tests` and there are empty `__init__.py` files. If it fails with "no tests collected", add `--no-header -rN` or a minimal test.
