---
Task ID: `T3`
Title: `Implement core models and Language enum with unit tests`
Sprint: `2026-03-02_module-core`
Module: `core`
Depends on: `T2`
Parallelizable: `yes, with T4, T5`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Create `nl_processing/core/models.py` with the four public interface types — `Language` enum, `ExtractedText`, `WordEntry`, and `TranslationResult` Pydantic models — and corresponding unit tests. After this task, any module can import these types from `core` for structured output enforcement and type-safe data contracts.

## Context (contract mapping)

- Requirements: `docs/planning-artifacts/prd.md` — CFR1 (`ExtractedText`), CFR2 (`WordEntry`), CFR3 (`TranslationResult`), CFR4 (`Language` enum), CFR5 (importable from core)
- Architecture: `docs/planning-artifacts/architecture.md` — "Core Package Structure (Flat)", Interface Contract in SPRINT.md
- Epics: `docs/planning-artifacts/epics.md` — Story 1.1: Core Pydantic Models & Language Enum

## Preconditions

- T1 completed — `nl_processing/core/` directory may not exist yet; create `__init__.py` (empty) and `models.py`
- T2 completed — `pydantic>=2.0,<3` is already in `pyproject.toml` (was there before T2; T2 added LangChain)

## Non-goals

- No exception classes (that is T4)
- No prompt loading utility (that is T5)
- No internal/intermediate models — only the public interface models defined in the architecture

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/core/__init__.py` (create, must be empty)
- `nl_processing/core/models.py` (create)
- `tests/unit/core/__init__.py` (create, must be empty)
- `tests/unit/core/test_models.py` (create)

**FORBIDDEN — this task must NEVER touch:**
- Any other module's code or tests
- `nl_processing/core/exceptions.py` (T4)
- `nl_processing/core/prompts.py` (T5)
- `pyproject.toml`
- Any docs outside `docs/sprints/module-core/`

**Test scope:**
- Tests go in: `tests/unit/core/test_models.py`
- Test command: `uv run pytest tests/unit/core/test_models.py -x -v`

## Touched surface (expected files / modules)

- `nl_processing/core/__init__.py` — created, empty
- `nl_processing/core/models.py` — created, contains all 4 types
- `tests/unit/core/__init__.py` — created, empty
- `tests/unit/core/test_models.py` — created, contains unit tests

## Dependencies and sequencing notes

- Depends on T2 (LangChain added) — though models.py itself only uses `pydantic` and `enum`, the directory structure is shared with T4/T5
- Can run in parallel with T4 (exceptions) and T5 (prompts) since they touch different files
- T7 depends on this task

## Third-party / library research (mandatory for any external dependency)

- **Library**: `pydantic` — version `>=2.0,<3` (already in `pyproject.toml`)
  - **Official documentation**: https://docs.pydantic.dev/latest/
  - **API reference**: https://docs.pydantic.dev/latest/api/base_model/
  - **Usage — BaseModel**:
    ```python
    from pydantic import BaseModel

    class ExtractedText(BaseModel):
        text: str
    ```
  - **Usage — with_structured_output()**: Pydantic v2 models work directly with LangChain's `with_structured_output()` — no `.schema()` needed. LangChain uses `.model_json_schema()` internally.
  - **Known gotchas**: Pydantic v2 uses `model_dump()` instead of `dict()`. Ensure tests use v2 API.

- **Library**: `enum` (stdlib)
  - **Official documentation**: https://docs.python.org/3/library/enum.html
  - **Usage**:
    ```python
    from enum import Enum
    class Language(Enum):
        NL = "nl"
        RU = "ru"
    ```

## Implementation steps (developer-facing)

1. **Create `nl_processing/core/` directory** (if not already present).
2. **Create `nl_processing/core/__init__.py`** — empty file (zero content). Required by ruff `strictly-empty-init-modules`.
3. **Create `nl_processing/core/models.py`** with the following contents:
   ```python
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
4. **Create `tests/unit/core/` directory** (if not already present).
5. **Create `tests/unit/core/__init__.py`** — empty file.
6. **Create `tests/unit/core/test_models.py`** with tests covering:
   - `Language` enum: `Language.NL.value == "nl"`, `Language.RU.value == "ru"`, enum members count == 2
   - `ExtractedText`: instantiation with `text="hello"`, serialization via `model_dump()`, JSON schema contains `text` field
   - `WordEntry`: instantiation with `normalized_form="de fiets"` and `word_type="noun"`, both fields accessible
   - `TranslationResult`: instantiation with `translation="дом"`, field accessible
   - Validation error: instantiation without required fields raises `ValidationError`
7. **Run tests**: `uv run pytest tests/unit/core/test_models.py -x -v`
8. **Run linting**: `uv run ruff format nl_processing/core/models.py tests/unit/core/test_models.py && uv run ruff check nl_processing/core/models.py tests/unit/core/test_models.py`

## Production safety constraints (mandatory)

- **Database operations**: None — pure data model definitions.
- **Resource isolation**: No shared resources. Library code only.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Using Pydantic BaseModel and stdlib Enum — no custom base classes.
- **Correct libraries only**: `pydantic>=2.0,<3` from `pyproject.toml`, `enum` from stdlib.
- **Correct file locations**: `nl_processing/core/models.py` per architecture spec.
- **No regressions**: New files — no existing functionality affected.

## Error handling + correctness rules (mandatory)

- Pydantic models enforce required fields by default — no need for custom validation.
- Do not add default values to model fields unless explicitly required (fail loudly on missing fields).

## Zero legacy tolerance rule (mandatory)

- No legacy to remove — these are new files.
- Ensure no `__init__.py` re-exports (empty `__init__.py` enforced by ruff).

## Acceptance criteria (testable)

1. `from nl_processing.core.models import Language, ExtractedText, WordEntry, TranslationResult` succeeds
2. `Language.NL.value == "nl"` and `Language.RU.value == "ru"`
3. `ExtractedText(text="hello").text == "hello"`
4. `WordEntry(normalized_form="de fiets", word_type="noun").normalized_form == "de fiets"`
5. `TranslationResult(translation="дом").translation == "дом"`
6. Missing required fields raise `pydantic.ValidationError`
7. `uv run pytest tests/unit/core/test_models.py -x -v` passes
8. `uv run ruff check nl_processing/core/models.py tests/unit/core/test_models.py` passes
9. `nl_processing/core/__init__.py` is empty
10. `nl_processing/core/models.py` is under 200 lines

## Verification / quality gates

- [ ] Unit tests added in `tests/unit/core/test_models.py`
- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] Negative-path tests exist (missing required fields → ValidationError)

## Edge cases

- `Language` enum should not accept arbitrary string values — `Language("invalid")` should raise `ValueError`
- Empty string for model fields is valid (Pydantic does not reject `""` for `str` by default) — this is acceptable per architecture

## Rollout / rollback (if relevant)

- Rollout: Create files in a single commit.
- Rollback: Delete the created files.

## Notes / risks

- **Risk**: Future modules may request additional model fields. **Mitigation**: Pydantic models are easily extensible — add fields in future sprints. Keep models minimal now per spec.
