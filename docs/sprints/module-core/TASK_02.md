---
Task ID: `T2`
Title: `Add langchain dependencies to pyproject.toml`
Sprint: `2026-03-02_module-core`
Module: `core`
Depends on: `T1`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Add `langchain` and `langchain-openai` as project-level dependencies to `pyproject.toml` so that the core prompt loading utility and all downstream modules can import LangChain components. After this task, `uv sync --all-groups` installs both packages.

## Context (contract mapping)

- Requirements: `docs/planning-artifacts/prd.md` — SNFR6 (project-level dependencies: `langchain`, `langchain-openai`, `pydantic`), SNFR7 (all modules depend on `langchain` and `langchain-openai` directly)
- Architecture: `docs/planning-artifacts/architecture.md` — "No Engine Abstraction — Modules Use LangChain Directly", "Technical Constraints & Dependencies" section
- Related: `pyproject.toml` (current dependency list)

## Preconditions

- T1 completed — legacy cleanup done, broken imports eliminated
- `pyproject.toml` exists and is editable

## Non-goals

- No code implementation — only dependency declarations
- No lockfile manual editing — `uv sync` handles that
- No Doppler setup — that is out of scope for this sprint

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `pyproject.toml` — add `langchain` and `langchain-openai` dependencies

**FORBIDDEN — this task must NEVER touch:**
- Any Python source code files
- Any test files
- Any docs outside `docs/sprints/module-core/`
- `ruff.toml`, `Makefile`, `pytest.ini`

**Test scope:**
- After modifying `pyproject.toml`, run: `uv sync --all-groups`
- Verify import works: `uv run python -c "from langchain_core.prompts import ChatPromptTemplate; print('OK')"`
- Verify import works: `uv run python -c "from langchain_openai import ChatOpenAI; print('OK')"`

## Touched surface (expected files / modules)

- `pyproject.toml` — add two dependencies to `[project] dependencies`

## Dependencies and sequencing notes

- Depends on T1 because the project must be in a clean state before adding dependencies
- T3, T4, T5 all depend on this task because they import from LangChain

## Third-party / library research (mandatory for any external dependency)

- **Library**: `langchain` — version range `>=0.3,<1`
  - **Official documentation**: https://python.langchain.com/docs/get_started/introduction
  - **API reference**: https://python.langchain.com/api_reference/core/prompts/langchain_core.prompts.chat.ChatPromptTemplate.html
  - **PyPI**: https://pypi.org/project/langchain/
  - **Usage**: Provides `ChatPromptTemplate` for prompt loading/serialization (used by `core/prompts.py`)
  - **Known gotchas**: LangChain 0.3 restructured into `langchain-core`, `langchain-community`, etc. The `ChatPromptTemplate` is in `langchain-core` (installed as a dependency of `langchain`).

- **Library**: `langchain-openai` — version range `>=0.3,<1`
  - **Official documentation**: https://python.langchain.com/docs/integrations/platforms/openai
  - **API reference**: https://python.langchain.com/api_reference/openai/chat_models/langchain_openai.chat_models.base.ChatOpenAI.html
  - **PyPI**: https://pypi.org/project/langchain-openai/
  - **Usage**: Provides `ChatOpenAI` for LLM invocation (used by all 4 pipeline modules)
  - **Known gotchas**: `langchain-openai` versions must be compatible with the installed `langchain-core` version. Using matching major version ranges (`>=0.3,<1` for both) ensures compatibility.

## Implementation steps (developer-facing)

1. Open `pyproject.toml`.
2. In the `[project] dependencies` list, add:
   - `"langchain>=0.3,<1"`
   - `"langchain-openai>=0.3,<1"`
3. The existing `"pydantic>=2.0,<3"` dependency stays unchanged.
4. Run `uv sync --all-groups` to install the new dependencies and update the lockfile.
5. Verify imports work:
   ```bash
   uv run python -c "from langchain_core.prompts import ChatPromptTemplate; print('OK')"
   uv run python -c "from langchain_openai import ChatOpenAI; print('OK')"
   ```

## Production safety constraints (mandatory)

- **Database operations**: None.
- **Resource isolation**: Adding dependencies to `pyproject.toml` does not affect the production instance (different directory, different virtualenv).
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Using existing, well-maintained LangChain ecosystem — no custom alternatives.
- **Correct libraries only**: Version ranges (`>=0.3,<1`) come from the architecture doc (`docs/planning-artifacts/architecture.md`, scope section and SPRINT.md).
- **Correct file locations**: Only `pyproject.toml` is modified.
- **No regressions**: Adding dependencies does not break existing code. `uv sync` resolves any version conflicts.

## Error handling + correctness rules (mandatory)

- N/A — this task modifies only project metadata, not code.

## Zero legacy tolerance rule (mandatory)

- No legacy to remove — this is a pure addition.

## Acceptance criteria (testable)

1. `pyproject.toml` contains `"langchain>=0.3,<1"` in `[project] dependencies`
2. `pyproject.toml` contains `"langchain-openai>=0.3,<1"` in `[project] dependencies`
3. `uv sync --all-groups` completes without errors
4. `uv run python -c "from langchain_core.prompts import ChatPromptTemplate"` succeeds
5. `uv run python -c "from langchain_openai import ChatOpenAI"` succeeds

## Verification / quality gates

- [x] `uv sync --all-groups` succeeds
- [x] LangChain imports work
- [x] No other files modified

## Edge cases

- If `uv.lock` has conflicts with new dependencies, `uv sync` will resolve them automatically. If not resolvable, widen version ranges (but this is unlikely given the broad `>=0.3,<1` range).

## Rollout / rollback (if relevant)

- Rollout: Single `pyproject.toml` edit + `uv sync`.
- Rollback: Revert `pyproject.toml` change, run `uv sync` again.

## Notes / risks

- **Risk**: LangChain version incompatibility with existing `pydantic>=2.0,<3`. **Mitigation**: LangChain 0.3+ supports Pydantic v2 natively — no conflict expected.
