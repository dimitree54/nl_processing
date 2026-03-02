---
Sprint ID: `2026-03-02_module-core`
Sprint Goal: `Deliver the shared core package (models, exceptions, prompt utilities) and clean up all broken legacy files that block make check`
Sprint Type: `module`
Module: `core`
Status: `planning`
Owners: `Developer`
---

## Goal

Implement the `nl_processing/core/` package providing shared Pydantic interface models (`ExtractedText`, `WordEntry`, `TranslationResult`, `Language` enum), typed exceptions (`APIError`, `TargetLanguageNotFoundError`, `UnsupportedImageFormatError`), a prompt loading utility, and a prompt authoring helper script. Additionally, clean up all broken legacy files (non-empty `__init__.py` files, dead test files referencing the non-existent `nl_processing.processor` module) so that `make check` passes on the core sprint's test scope. Add missing `langchain`/`langchain-openai` dependencies to `pyproject.toml`.

## Module Scope

### What this sprint implements
- Module: `core` — shared infrastructure package consumed by all 4 pipeline modules
- Architecture spec: `docs/planning-artifacts/architecture.md` (Core Package section)

### Boundary Rules (STRICTLY ENFORCED)

**ALLOWED — this sprint may ONLY touch:**
- `nl_processing/core/__init__.py` (create, must be empty)
- `nl_processing/core/models.py` (create)
- `nl_processing/core/exceptions.py` (create)
- `nl_processing/core/prompts.py` (create)
- `nl_processing/core/scripts/prompt_author.py` (create)
- `tests/unit/core/__init__.py` (create)
- `tests/unit/core/test_models.py` (create)
- `tests/unit/core/test_exceptions.py` (create)
- `tests/unit/core/test_prompts.py` (create)
- `pyproject.toml` (modify — add `langchain`, `langchain-openai` dependencies)
- `vulture_whitelist.py` (modify if needed)
- **Legacy cleanup files (broken, must be fixed/removed):**
  - `nl_processing/__init__.py` (make empty — currently imports from non-existent `nl_processing.processor`)
  - `nl_processing/extract_words_from_text/__init__.py` (make empty — currently has re-exports violating ruff)
  - `nl_processing/translate_text/__init__.py` (make empty — currently has re-exports violating ruff)
  - `nl_processing/translate_word/__init__.py` (make empty — currently has re-exports violating ruff)
  - `nl_processing/database/__init__.py` (make empty — currently has re-exports violating ruff)
  - `tests/unit/test_processor_unit.py` (delete — references non-existent `nl_processing.processor`)
  - `tests/integration/test_processor_integration.py` (delete — references non-existent `nl_processing.processor`)
  - `tests/e2e/test_smoke_e2e.py` (delete — references non-existent `nl_processing.processor` via `__init__.py`)
  - `tests/e2e/conftest.py` (delete — defines obsolete pytest CLI option for removed e2e test)
  - `vulture_whitelist.py` (rewrite — currently references deleted `conftest.py`)
  - `tests/unit/database/test_database.py` (delete — imports from broken `nl_processing` `__init__`, and `database` module is out of scope for this architecture)

**FORBIDDEN — this sprint must NEVER touch:**
- `nl_processing/extract_text_from_image/` (any files — owned by module-extract-text-from-image sprint)
- `nl_processing/extract_words_from_text/service.py` (owned by future sprint)
- `nl_processing/translate_text/service.py` (owned by future sprint)
- `nl_processing/translate_word/service.py` (owned by future sprint)
- `nl_processing/database/service.py` (out of scope)
- `tests/unit/extract_text_from_image/` (owned by module-extract-text-from-image sprint)
- `tests/unit/extract_words_from_text/` (owned by future sprint)
- `tests/unit/translate_text/` (owned by future sprint)
- `tests/unit/translate_word/` (owned by future sprint)
- Any docs outside `docs/sprints/module-core/`
- Requirements/architecture docs

### Test Scope
- **Test directory**: `tests/unit/core/`
- **Test command**: `uv run pytest tests/unit/core/ -x -v`
- **Full validation**: `make check` (must pass after all tasks — unit tests for core + no broken imports anywhere)
- **NEVER run**: tests from other modules in isolation (but `make check` runs everything — it must all pass)

## Interface Contract

### Public interface this sprint implements

```python
# nl_processing/core/models.py
from enum import Enum
from pydantic import BaseModel

class Language(Enum):
    NL = "nl"
    RU = "ru"

class ExtractedText(BaseModel):
    text: str

class WordEntry(BaseModel):
    normalized_form: str
    word_type: str

class TranslationResult(BaseModel):
    translation: str
```

```python
# nl_processing/core/exceptions.py
class APIError(Exception): ...
class TargetLanguageNotFoundError(Exception): ...
class UnsupportedImageFormatError(Exception): ...
```

```python
# nl_processing/core/prompts.py
from langchain_core.prompts import ChatPromptTemplate

def load_prompt(prompt_path: str) -> ChatPromptTemplate: ...
```

## Scope

### In
- `core/models.py` — Pydantic models and Language enum (CFR1-5)
- `core/exceptions.py` — typed exceptions (CFR6-9)
- `core/prompts.py` — prompt loading utility (CFR10, CFR13-14)
- `core/scripts/prompt_author.py` — dev-time prompt authoring helper (CFR12)
- `pyproject.toml` — add `langchain>=0.3,<1`, `langchain-openai>=0.3,<1` dependencies (SNFR6-7)
- Unit tests for all core components (CNFR2)
- Legacy cleanup: make all `__init__.py` files empty, remove dead test files
- `vulture_whitelist.py` update

### Out
- No module implementations (those are separate sprints)
- No integration or e2e tests for core (core is internal infrastructure; unit tests only per CNFR2)
- No CI pipeline setup (`.github/workflows/ci.yml`) — not in scope per user request
- No `.doppler.yaml` creation
- No Makefile changes

## Inputs (contracts)

- Requirements: `docs/planning-artifacts/prd.md` (Core Functional Requirements CFR1-14, Core NFRs CNFR1-2)
- Architecture: `docs/planning-artifacts/architecture.md` (Core Package sections, Code Style & Quality, Implementation Patterns)
- Related constraints: `ruff.toml` (strictly-empty-init-modules, banned APIs), `Makefile` (quality gate)

## Change digest

- **Requirement deltas**: None — first implementation of core package
- **Architecture deltas**: None — implementing as specified

## Task list (dependency-aware)

- **T1:** `TASK_01.md` (depends: —) (parallel: no) — Legacy cleanup: empty all `__init__.py` files, remove dead tests, update vulture whitelist
- **T2:** `TASK_02.md` (depends: T1) (parallel: no) — Add langchain dependencies to pyproject.toml
- **T3:** `TASK_03.md` (depends: T2) (parallel: no) — Implement core models and Language enum with unit tests
- **T4:** `TASK_04.md` (depends: T2) (parallel: yes, with T3) — Implement core exceptions with unit tests
- **T5:** `TASK_05.md` (depends: T2) (parallel: yes, with T3, T4) — Implement prompt loading utility with unit tests
- **T6:** `TASK_06.md` (depends: T5) (parallel: no) — Implement prompt authoring helper script
- **T7:** `TASK_07.md` (depends: T3, T4, T5, T6) (parallel: no) — Final verification: make check passes

## Dependency graph (DAG)

- T1 → T2
- T2 → T3
- T2 → T4
- T2 → T5
- T5 → T6
- T3, T4, T5, T6 → T7

## Execution plan

### Critical path
- T1 → T2 → T5 → T6 → T7

### Parallel tracks (lanes)
- **Lane A**: T3 (models)
- **Lane B**: T4 (exceptions)
- **Lane C**: T5 → T6 (prompts)
- All three lanes can run in parallel after T2. T7 waits for all.

## Production safety

The current application version is **running in production on this same machine** (different directory).

- **Production database**: NOT modified during this sprint. Core has no database interactions.
- **Shared resource isolation**: Core package is a library — no ports, sockets, or file paths. Tests run in-process only. No production resource collisions possible.
- **Migration deliverable**: N/A — no data model changes

## Definition of Done (DoD)

All items must be true:

- All tasks completed and verified
- Core unit tests pass: `uv run pytest tests/unit/core/ -x -v`
- `make check` passes completely (all linters, all test directories)
- Module isolation: no files outside the ALLOWED list were touched
- Public interface matches architecture spec exactly
- Zero legacy tolerance: all broken `__init__.py` files emptied, all dead test files removed
- No errors are silenced (no swallowed exceptions)
- Requirements/architecture docs unchanged
- Production database untouched
- No shared local resources conflict with production instance

## Risks + mitigations

- **Risk**: LangChain `ChatPromptTemplate` serialization format may have changed across versions
  - **Mitigation**: T5 includes web research for the exact current format and API. Pin version range in pyproject.toml.
- **Risk**: Emptying other modules' `__init__.py` files may break their existing test files (e.g., `tests/unit/database/test_database.py` imports from `nl_processing` root)
  - **Mitigation**: T1 explicitly removes all test files that depend on broken imports. Other module sprints will recreate their tests.
- **Risk**: `vulture_whitelist.py` references deleted `conftest.py` — vulture will fail
  - **Mitigation**: T1 updates `vulture_whitelist.py` to remove the stale reference.

## Migration plan (if data model changes)

N/A — no data model changes

## Rollback / recovery notes

- Revert all files in ALLOWED list to their previous state via git.
- No database or external state to roll back.

## Task validation status

- Per-task validation order: `T1` → `T2` → `T3` → `T4` → `T5` → `T6` → `T7`
- Validator: `task-checker`
- Outcome: `pending`
- Notes: —

## Sources used

- Requirements: `docs/planning-artifacts/prd.md` (CFR1-14, CNFR1-2, SFR1-14, SNFR1-19)
- Architecture: `docs/planning-artifacts/architecture.md` (full document)
- Epics: `docs/planning-artifacts/epics.md` (Epic 1)
- Code read: `nl_processing/__init__.py`, `nl_processing/*/\__init__.py`, `tests/unit/test_processor_unit.py`, `tests/integration/test_processor_integration.py`, `tests/e2e/test_smoke_e2e.py`, `tests/e2e/conftest.py`, `vulture_whitelist.py`, `pyproject.toml`, `ruff.toml`, `Makefile`, `pytest.ini`, `.jscpd.json`

## Contract summary

### What (requirements)
- CFR1-5: Pydantic models (`ExtractedText`, `WordEntry`, `TranslationResult`, `Language` enum) importable from core
- CFR6-9: Typed exceptions (`APIError`, `TargetLanguageNotFoundError`, `UnsupportedImageFormatError`) importable from core
- CFR10-14: Prompt loading utility using LangChain `ChatPromptTemplate` native serialization; prompt authoring helper script
- CNFR1-2: Core is internal infrastructure with its own unit tests

### How (architecture)
- Flat package structure: `models.py`, `exceptions.py`, `prompts.py`, `scripts/prompt_author.py`
- Empty `__init__.py` (ruff strictly-empty-init-modules)
- Direct imports: `from nl_processing.core.models import Language`
- LangChain `ChatPromptTemplate` native serialization for prompt JSON files
- `os.environ['KEY']` pattern (never `os.getenv`)
- 200-line file limit, no `Any`, no relative imports

## Impact inventory (implementation-facing)

- **Module**: `core` — `nl_processing/core/`
- **Interfaces**: `models.py` exports (`Language`, `ExtractedText`, `WordEntry`, `TranslationResult`); `exceptions.py` exports (`APIError`, `TargetLanguageNotFoundError`, `UnsupportedImageFormatError`); `prompts.py` exports (`load_prompt`)
- **Data model**: Pydantic models for structured output (no database)
- **External services**: None (core does not call APIs)
- **Test directory**: `tests/unit/core/`
