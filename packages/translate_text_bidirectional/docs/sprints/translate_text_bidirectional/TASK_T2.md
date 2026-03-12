---
Task ID: `T2`
Title: `Package scaffolding for translate_text_bidirectional`
Sprint: `2026-03-12_translate-text-bidirectional`
Module: `translate_text_bidirectional`
Depends on: `T1`
Parallelizable: no
Owner: Developer
Status: planned
---

## Goal / value

Create the full package directory structure, configuration files, and empty `__init__.py` modules for `translate_text_bidirectional`, following the exact conventions of `translate_text`. After this task, the package skeleton exists and `make check` runs (even if there are no real tests yet).

## Context (contract mapping)

- Module spec: `packages/translate_text_bidirectional/docs/module-spec.md` — Package and Documentation Location section
- Reference: `packages/translate_text/pyproject.toml`, `Makefile`, `pytest.ini`, `ruff.toml`
- Reference: `packages/translate_text/` directory structure

## Preconditions

- T1 completed (core extension exists, though not strictly required for scaffolding — dependency ensures ordering).

## Non-goals

- Writing any service code (T4).
- Writing prompt assets (T3).
- Writing real test logic (T4–T6).
- Monorepo root integration (T7).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `packages/translate_text_bidirectional/` — create all package structure

**FORBIDDEN — this task must NEVER touch:**
- `packages/translate_text/` — reference only
- `packages/core/` — already extended in T1
- Root `pyproject.toml`, `Makefile`, `ruff.toml` — deferred to T7
- Any other package

**Test scope:**
- Tests go in: `packages/translate_text_bidirectional/tests/`
- Test command: `make check` from `packages/translate_text_bidirectional/`
- Create test directory structure with empty `__init__.py` files

## Touched surface (expected files / modules)

### Source layout
- `packages/translate_text_bidirectional/src/nl_processing/translate_text_bidirectional/__init__.py`
- `packages/translate_text_bidirectional/src/nl_processing/translate_text_bidirectional/service.py` (empty placeholder or minimal)
- `packages/translate_text_bidirectional/src/nl_processing/translate_text_bidirectional/prompts/` (directory only)

### Config files
- `packages/translate_text_bidirectional/pyproject.toml`
- `packages/translate_text_bidirectional/Makefile`
- `packages/translate_text_bidirectional/pytest.ini`
- `packages/translate_text_bidirectional/ruff.toml`

### Test layout
- `packages/translate_text_bidirectional/tests/__init__.py`
- `packages/translate_text_bidirectional/tests/conftest.py`
- `packages/translate_text_bidirectional/tests/unit/__init__.py`
- `packages/translate_text_bidirectional/tests/unit/translate_text_bidirectional/__init__.py`
- `packages/translate_text_bidirectional/tests/unit/translate_text_bidirectional/conftest.py`
- `packages/translate_text_bidirectional/tests/integration/__init__.py`
- `packages/translate_text_bidirectional/tests/integration/translate_text_bidirectional/__init__.py`
- `packages/translate_text_bidirectional/tests/e2e/__init__.py`
- `packages/translate_text_bidirectional/tests/e2e/translate_text_bidirectional/__init__.py`

## Dependencies and sequencing notes

- Depends on T1 for ordering. The scaffold itself does not use the core extension yet.
- T3 needs the `prompts/` directory. T4 needs the service file and test directories.

## Third-party / library research (mandatory for any external dependency)

No new third-party dependencies introduced in this task. The `pyproject.toml` will declare the same dependencies as `translate_text`:
- `nl-processing-core` (local path dependency)
- `langchain-core>=0.3,<1`
- `pydantic>=2.0,<3`

Dev dependencies mirror `translate_text`:
- `pytest>=9.0.2,<10`
- `pytest-asyncio>=1.3.0,<2`
- `pytest-xdist>=3.8.0,<4`
- `ruff>=0.15.0,<0.16`
- `pylint>=4.0.4,<5`
- `vulture>=2.14.0,<3`

## Implementation steps (developer-facing)

1. **Create `pyproject.toml`** mirroring `translate_text/pyproject.toml`:
   ```toml
   [build-system]
   requires = ["setuptools", "wheel"]
   build-backend = "setuptools.build_meta"

   [project]
   name = "nl-processing-translate-text-bidirectional"
   version = "1.0.0"
   description = "Bidirectional text translation package for nl_processing"
   requires-python = ">=3.12"
   dependencies = [
     "nl-processing-core",
     "langchain-core>=0.3,<1",
     "pydantic>=2.0,<3",
   ]

   [tool.setuptools.packages.find]
   where = ["src"]
   include = ["nl_processing.translate_text_bidirectional*"]
   namespaces = true

   [tool.setuptools.package-data]
   "nl_processing.translate_text_bidirectional.prompts" = ["*.json"]

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

2. **Create `Makefile`** mirroring `translate_text/Makefile`:
   ```makefile
   ROOT_DIR := $(abspath ../..)
   TOOLS_VENV ?= $(shell if [ -x "$(CURDIR)/.venv/bin/pytest" ] && ... ; then printf '%s' "$(CURDIR)/.venv"; else printf '%s' "$(ROOT_DIR)/.venv"; fi)

   .PHONY: check

   check:
   	$(MAKE) -C "$(ROOT_DIR)" package-check PKG=translate_text_bidirectional PACKAGE_PYTHONPATH=src:../core/src TOOLS_VENV="$(TOOLS_VENV)"
   ```
   Copy the exact `TOOLS_VENV` detection logic from `translate_text/Makefile`.

3. **Create `pytest.ini`** — copy from `translate_text/pytest.ini` verbatim.

4. **Create `ruff.toml`** — copy from `translate_text/ruff.toml` verbatim:
   ```toml
   extend = "../../ruff.toml"
   src = ["src", "tests"]
   ```

5. **Create source directory tree**:
   - `src/nl_processing/translate_text_bidirectional/__init__.py` (empty)
   - `src/nl_processing/translate_text_bidirectional/prompts/` (empty directory — T3 will populate)

6. **Create test directory tree** with empty `__init__.py` files:
   - `tests/__init__.py`
   - `tests/conftest.py` (copy pattern from `translate_text/tests/conftest.py` — `AsyncChainMock`, `AsyncChainMockError`, `make_tool_response`)
   - `tests/unit/__init__.py`
   - `tests/unit/translate_text_bidirectional/__init__.py`
   - `tests/unit/translate_text_bidirectional/conftest.py` (minimal, re-exports from `tests.conftest`)
   - `tests/integration/__init__.py`
   - `tests/integration/translate_text_bidirectional/__init__.py`
   - `tests/e2e/__init__.py`
   - `tests/e2e/translate_text_bidirectional/__init__.py`

7. **Adapt `tests/conftest.py`** for bidirectional tool responses. The mock must support responses where the tool name varies (either direction tool). Update `make_tool_response` to accept both a text value and an optional tool name.

8. **Verify** `make check` runs from the package directory (it will run ruff format/check, pylint, and pytest on the empty test suite). Fix any config issues.

## Production safety constraints (mandatory)

- No database operations.
- No ports or shared resources.
- Pure file creation — no runtime impact.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: All config files mirror `translate_text` patterns exactly.
- **Correct libraries only**: Versions match `translate_text/pyproject.toml`.
- **Correct file locations**: Follow exact `src/nl_processing/<package>/` layout convention.

## Error handling + correctness rules (mandatory)

- N/A for scaffolding — no runtime code yet.

## Zero legacy tolerance rule (mandatory)

- No legacy exists — fresh package.

## Acceptance criteria (testable)

1. Directory structure matches the layout described in "Touched surface" above.
2. `pyproject.toml` declares correct package name, dependencies, and namespaced package discovery.
3. `Makefile` delegates to root `package-check` with correct `PKG` and `PACKAGE_PYTHONPATH`.
4. `ruff.toml` extends root config with correct `src` paths.
5. `pytest.ini` matches `translate_text` conventions.
6. `make check` from `packages/translate_text_bidirectional/` passes (ruff, pylint, empty pytest).
7. All files stay under 200 lines.

## Verification / quality gates

- [ ] `make check` passes from `packages/translate_text_bidirectional/`
- [ ] `ruff format` and `ruff check` report no issues
- [ ] `pylint` reports no issues (max-module-lines=200, bad-builtins gate)
- [ ] All `__init__.py` files are empty (per `ruff.toml` `strictly-empty-init-modules`)
- [ ] No new warnings introduced

## Edge cases

- Ensure `__init__.py` under `src/nl_processing/` namespace is NOT created (namespace package — implicit namespace discovery via `setuptools`).

## Notes / risks

- **Risk**: Missing `__init__.py` at the right levels could break namespace packaging.
  - **Mitigation**: Follow `translate_text` exactly — `src/nl_processing/` has no `__init__.py`; `src/nl_processing/translate_text_bidirectional/` has one.
