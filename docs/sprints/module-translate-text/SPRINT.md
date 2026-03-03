---
Sprint ID: `2026-03-03_translate-text`
Sprint Goal: `Replace the legacy translate_text stub with a fully functional LangChain-powered TextTranslator class that translates Dutch text to Russian with markdown preservation.`
Sprint Type: `module`
Module: `translate_text`
Status: `planning`
---

## Goal

Replace the legacy `translate_text` function (a string-formatting stub) with a production-quality `TextTranslator` class that uses LangChain tool calling to translate Dutch text to Russian. The module must preserve markdown formatting, return clean output (no LLM chatter), handle edge cases (empty input, non-Dutch text), and validate language pairs at init time. All 3 test levels must pass.

## Module Scope

### What this sprint implements
- Module: `translate_text`
- Architecture spec: `nl_processing/translate_text/docs/architecture_translate_text.md`
- PRD: `nl_processing/translate_text/docs/prd_translate_text.md`
- Epics reference: `docs/planning-artifacts/epics.md` -- Epic 4

### Boundary Rules (STRICTLY ENFORCED)

**ALLOWED -- this sprint may ONLY touch:**
- `nl_processing/translate_text/service.py` -- replace legacy stub with `TextTranslator` class
- `nl_processing/translate_text/prompts/` -- create directory, prompt generation script, prompt JSON
- `tests/unit/translate_text/` -- unit tests (create conftest.py, test files)
- `tests/integration/translate_text/` -- integration tests (create directory and test files)
- `tests/e2e/translate_text/` -- e2e tests (create directory and test files)
- `vulture_whitelist.py` -- update stale `translate_text` reference

**FORBIDDEN -- this sprint must NEVER touch:**
- `nl_processing/core/` -- core package
- `nl_processing/extract_text_from_image/` -- different module
- `nl_processing/extract_words_from_text/` -- different module
- `nl_processing/translate_word/` -- different module
- `nl_processing/database/` -- different module
- Tests of other modules at any level
- Any bot code
- `pyproject.toml`, `Makefile`, `ruff.toml`, `pytest.ini` -- project-level config

### Test Scope
- **Unit test directory**: `tests/unit/translate_text/`
- **Unit test command**: `uv run pytest tests/unit/translate_text/ -x -v`
- **Integration test directory**: `tests/integration/translate_text/`
- **Integration test command**: `doppler run -- uv run pytest tests/integration/translate_text/ -x -v`
- **E2e test directory**: `tests/e2e/translate_text/`
- **E2e test command**: `doppler run -- uv run pytest tests/e2e/translate_text/ -x -v`
- **NEVER run**: full test suite or tests from other modules

## Interface Contract

### Public interface this sprint implements

```python
from nl_processing.translate_text.service import TextTranslator
from nl_processing.core.models import Language

translator = TextTranslator(source_language=Language.NL, target_language=Language.RU)
result: str = await translator.translate(text)
```

- Constructor: `__init__(self, *, source_language: Language, target_language: Language, model: str = "gpt-4.1-mini") -> None`
- Method: `async translate(self, text: str) -> str`
- Returns empty string for empty input or non-source-language text
- Raises descriptive exception at init for unsupported language pairs
- Raises `APIError` for upstream API failures

## Scope

### In
- Prompt generation script (`generate_nl_ru_prompt.py`) + Dutch-to-Russian prompt JSON (`nl_ru.json`) with few-shot examples
- `TextTranslator` class in `service.py` (replacing the legacy `translate_text` function)
- Unit tests with mocked chain
- Integration tests with real API calls (output cleanliness, Cyrillic check, markdown preservation, performance)
- E2e tests with full translation scenarios
- Vulture whitelist update

### Out
- Language pairs other than Dutch-to-Russian
- Markdown code block special handling
- Automated semantic quality scoring
- Any changes to core models or exceptions

## Inputs (contracts)

- Requirements: `nl_processing/translate_text/docs/prd_translate_text.md`
- Architecture: `nl_processing/translate_text/docs/architecture_translate_text.md`
- Shared architecture: `docs/planning-artifacts/architecture.md`
- Shared PRD: `docs/planning-artifacts/prd.md`
- Epics: `docs/planning-artifacts/epics.md` -- Epic 4
- Reference implementation: `nl_processing/extract_text_from_image/service.py`

## Change digest

- **Requirement deltas**: None. Implementing TT-FR1 through TT-FR10 and TT-NFR1 through TT-NFR2 from scratch.
- **Architecture deltas**: None. Following shared patterns.

## Task list (dependency-aware)

- **T1:** `TASK_prompt_generation.md` (depends: --) (parallel: no) -- Create NL->RU translation prompt with few-shot examples
- **T2:** `TASK_service_implementation.md` (depends: T1) (parallel: no) -- Implement TextTranslator class, replacing legacy stub
- **T3:** `TASK_unit_tests.md` (depends: T2) (parallel: no) -- Create unit tests with mocked chain
- **T4:** `TASK_integration_tests.md` (depends: T2) (parallel: yes, with T5) -- Create integration tests with real API calls
- **T5:** `TASK_e2e_tests.md` (depends: T2) (parallel: yes, with T4) -- Create e2e tests
- **T6:** `TASK_vulture_cleanup.md` (depends: T2) (parallel: yes, with T3/T4/T5) -- Update vulture whitelist

## Dependency graph (DAG)

- T1 -> T2
- T2 -> T3
- T2 -> T4
- T2 -> T5
- T2 -> T6

## Execution plan

### Critical path
- T1 -> T2 -> T3 -> T4

### Parallel tracks (lanes)
- **Lane A (critical)**: T1, T2, T3
- **Lane B (after T2)**: T4 || T5 || T6

## Production safety

- **Production database**: N/A -- no database interactions.
- **Shared resource isolation**: N/A -- OpenAI API calls only, no local resources.
- **Migration deliverable**: N/A -- no data model changes.

## Definition of Done (DoD)

All items must be true:

- All tasks completed and verified
- Unit tests pass: `uv run pytest tests/unit/translate_text/ -x -v`
- Integration tests pass: `doppler run -- uv run pytest tests/integration/translate_text/ -x -v`
- E2e tests pass: `doppler run -- uv run pytest tests/e2e/translate_text/ -x -v`
- Module isolation: no files outside the ALLOWED list were touched
- Public interface matches architecture spec (`TextTranslator` with `translate` method)
- Zero legacy tolerance: legacy `translate_text` function removed, vulture whitelist updated
- No errors are silenced
- Requirements/architecture docs unchanged
- `make check` passes fully

## Risks + mitigations

- **Risk**: Few-shot prompt quality may not produce natural-sounding Russian translations.
  - **Mitigation**: Curate high-quality few-shot examples. Human review of examples during development.
- **Risk**: Markdown preservation may be inconsistent.
  - **Mitigation**: Include markdown-specific few-shot examples. Test structural preservation.
- **Risk**: Language pair validation logic adds complexity.
  - **Mitigation**: Simple pattern -- only NL->RU supported. Check at init, raise ValueError.

## Migration plan (if data model changes)

N/A -- no data model changes.

## Rollback / recovery notes

- Revert all files in the ALLOWED list to their previous state

## Task validation status

- Per-task validation order: `T1` -> `T2` -> `T3` -> `T4` -> `T5` -> `T6`
- Validator: `self-validated`
- Outcome: `approved`

## Sources used

- Requirements: `nl_processing/translate_text/docs/prd_translate_text.md`
- Architecture: `nl_processing/translate_text/docs/architecture_translate_text.md`
- Shared architecture: `docs/planning-artifacts/architecture.md`
- Shared PRD: `docs/planning-artifacts/prd.md`
- Epics: `docs/planning-artifacts/epics.md`
- Code read: `nl_processing/extract_text_from_image/service.py`, `nl_processing/translate_text/service.py` (legacy stub), `vulture_whitelist.py`, `nl_processing/core/models.py`, `nl_processing/core/exceptions.py`

## Contract summary

### What (requirements)
- TT-FR1-10: Translate Dutch to Russian with markdown preservation, clean output, natural style
- TT-NFR1-2: <5s for ~100 words, <1s init

### How (architecture)
- `TextTranslator` class using LangChain `ChatOpenAI.bind_tools()` with internal Pydantic wrapper
- Source+target language constructor, language pair validation at init
- Returns plain `str`, structured output used internally only
- Empty string for empty input / non-Dutch text
- Few-shot prompt examples as core asset (`nl_ru.json`)

## Impact inventory (implementation-facing)

- **Module**: `translate_text` (`nl_processing/translate_text/`)
- **Interfaces**: `TextTranslator.translate(text: str) -> str`
- **Data model**: Returns plain `str`, uses internal Pydantic model for tool calling
- **External services**: OpenAI API via LangChain
- **Test directories**: `tests/unit/translate_text/`, `tests/integration/translate_text/`, `tests/e2e/translate_text/`
