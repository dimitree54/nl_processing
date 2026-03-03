---
Sprint ID: `2026-03-03_translate-word`
Sprint Goal: `Replace the legacy translate_word stub with a fully functional LangChain-powered WordTranslator class that translates batches of Dutch words to Russian.`
Sprint Type: `module`
Module: `translate_word`
Status: `planning`
---

## Goal

Replace the legacy `translate_word` function (a dictionary-lookup stub) with a production-quality `WordTranslator` class that uses LangChain tool calling to translate batches of Dutch words/phrases to Russian in a single API call. The module must maintain one-to-one order-preserving mapping between input and output, handle empty input without API calls, and meet the <1s performance target for 10 words. All 3 test levels must pass.

## Module Scope

### What this sprint implements
- Module: `translate_word`
- Architecture spec: `nl_processing/translate_word/docs/architecture_translate_word.md`
- PRD: `nl_processing/translate_word/docs/prd_translate_word.md`
- Epics reference: `docs/planning-artifacts/epics.md` -- Epic 5

### Boundary Rules (STRICTLY ENFORCED)

**ALLOWED -- this sprint may ONLY touch:**
- `nl_processing/translate_word/service.py` -- replace legacy stub with `WordTranslator` class
- `nl_processing/translate_word/prompts/` -- create directory, prompt generation script, prompt JSON
- `tests/unit/translate_word/` -- unit tests (create conftest.py, test files)
- `tests/integration/translate_word/` -- integration tests (create directory and test files)
- `tests/e2e/translate_word/` -- e2e tests (create directory and test files)
- `vulture_whitelist.py` -- update stale `translate_word` reference

**FORBIDDEN -- this sprint must NEVER touch:**
- `nl_processing/core/` -- core package
- `nl_processing/extract_text_from_image/` -- different module
- `nl_processing/extract_words_from_text/` -- different module
- `nl_processing/translate_text/` -- different module
- `nl_processing/database/` -- different module
- Tests of other modules at any level
- Any bot code
- `pyproject.toml`, `Makefile`, `ruff.toml`, `pytest.ini` -- project-level config

### Test Scope
- **Unit test directory**: `tests/unit/translate_word/`
- **Unit test command**: `uv run pytest tests/unit/translate_word/ -x -v`
- **Integration test directory**: `tests/integration/translate_word/`
- **Integration test command**: `doppler run -- uv run pytest tests/integration/translate_word/ -x -v`
- **E2e test directory**: `tests/e2e/translate_word/`
- **E2e test command**: `doppler run -- uv run pytest tests/e2e/translate_word/ -x -v`
- **NEVER run**: full test suite or tests from other modules

## Interface Contract

### Public interface this sprint implements

```python
from nl_processing.translate_word.service import WordTranslator
from nl_processing.core.models import Language, TranslationResult

translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)
results: list[TranslationResult] = await translator.translate(["huis", "lopen", "snel"])
# len(results) == 3, order preserved
# results[0].translation == "дом"
```

- Constructor: `__init__(self, *, source_language: Language, target_language: Language, model: str = "gpt-4.1-mini") -> None`
- Method: `async translate(self, words: list[str]) -> list[TranslationResult]`
- Returns empty list for empty input (no API call)
- Raises `APIError` for upstream API failures
- One-to-one order-preserving: `len(output) == len(input)`

## Scope

### In
- Prompt generation script (`generate_nl_ru_prompt.py`) + NL->RU word translation prompt JSON (`nl_ru.json`)
- `WordTranslator` class in `service.py` (replacing the legacy `translate_word` function)
- Unit tests with mocked chain
- Integration tests (10-word quality test + performance test)
- E2e tests with full translation scenarios
- Vulture whitelist update

### Out
- Language pairs other than Dutch-to-Russian
- Additional fields in `TranslationResult`
- Deduplication or batch size limits
- Any changes to core models or exceptions

## Inputs (contracts)

- Requirements: `nl_processing/translate_word/docs/prd_translate_word.md`
- Architecture: `nl_processing/translate_word/docs/architecture_translate_word.md`
- Shared architecture: `docs/planning-artifacts/architecture.md`
- Shared PRD: `docs/planning-artifacts/prd.md`
- Epics: `docs/planning-artifacts/epics.md` -- Epic 5
- Reference implementation: `nl_processing/extract_text_from_image/service.py`

## Change digest

- **Requirement deltas**: None. Implementing TW-FR1 through TW-FR11 and TW-NFR1 through TW-NFR2 from scratch.
- **Architecture deltas**: None. Following shared patterns.

## Task list (dependency-aware)

- **T1:** `TASK_prompt_generation.md` (depends: --) (parallel: no) -- Create NL->RU word translation prompt with few-shot examples
- **T2:** `TASK_service_implementation.md` (depends: T1) (parallel: no) -- Implement WordTranslator class, replacing legacy stub
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
- **Shared resource isolation**: N/A -- OpenAI API calls only.
- **Migration deliverable**: N/A -- no data model changes.

## Definition of Done (DoD)

All items must be true:

- All tasks completed and verified
- Unit tests pass: `uv run pytest tests/unit/translate_word/ -x -v`
- Integration tests pass: `doppler run -- uv run pytest tests/integration/translate_word/ -x -v`
- E2e tests pass: `doppler run -- uv run pytest tests/e2e/translate_word/ -x -v`
- Module isolation: no files outside the ALLOWED list were touched
- Public interface matches architecture spec (`WordTranslator` with `translate` method)
- One-to-one order-preserving mapping verified in tests
- Zero legacy tolerance: legacy `translate_word` function and `_TRANSLATIONS` dict removed
- No errors are silenced
- Requirements/architecture docs unchanged
- `make check` passes fully

## Risks + mitigations

- **Risk**: One-to-one mapping may not be reliably enforced by the LLM.
  - **Mitigation**: Pydantic schema enforces list structure. Prompt explicitly instructs same-order, same-count output. Test validates `len(output) == len(input)`.
- **Risk**: <1s performance target may be tight for API round-trip.
  - **Mitigation**: Single API call for entire batch. Use fast model (`gpt-4.1-mini`). Performance test validates.
- **Risk**: Word translation quality may be inconsistent for ambiguous words.
  - **Mitigation**: Quality test uses 10 unambiguous words with clear ground-truth translations.

## Migration plan (if data model changes)

N/A -- no data model changes.

## Rollback / recovery notes

- Revert all files in the ALLOWED list to their previous state

## Task validation status

- Per-task validation order: `T1` -> `T2` -> `T3` -> `T4` -> `T5` -> `T6`
- Validator: `self-validated`
- Outcome: `approved`

## Sources used

- Requirements: `nl_processing/translate_word/docs/prd_translate_word.md`
- Architecture: `nl_processing/translate_word/docs/architecture_translate_word.md`
- Shared architecture: `docs/planning-artifacts/architecture.md`
- Shared PRD: `docs/planning-artifacts/prd.md`
- Epics: `docs/planning-artifacts/epics.md`
- Code read: `nl_processing/extract_text_from_image/service.py`, `nl_processing/translate_word/service.py` (legacy stub), `vulture_whitelist.py`, `nl_processing/core/models.py`

## Contract summary

### What (requirements)
- TW-FR1-11: Translate word batches Dutch->Russian with one-to-one mapping, <1s performance
- TW-NFR1-2: <1s for 10 words, single LLM call per batch

### How (architecture)
- `WordTranslator` class using LangChain `ChatOpenAI.bind_tools()` with wrapper Pydantic model
- Source+target language constructor, language pair validation at init
- Returns `list[TranslationResult]` (from core), one-to-one order-preserving
- Empty list for empty input (no API call)
- Single LLM call per batch (all words in one request)

## Impact inventory (implementation-facing)

- **Module**: `translate_word` (`nl_processing/translate_word/`)
- **Interfaces**: `WordTranslator.translate(words: list[str]) -> list[TranslationResult]`
- **Data model**: Uses `TranslationResult` from `core` (already defined)
- **External services**: OpenAI API via LangChain
- **Test directories**: `tests/unit/translate_word/`, `tests/integration/translate_word/`, `tests/e2e/translate_word/`
