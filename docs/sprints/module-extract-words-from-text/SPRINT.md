---
Sprint ID: `2026-03-03_extract-words-from-text`
Sprint Goal: `Replace the legacy regex stub with a fully functional LangChain-powered WordExtractor class that extracts and normalizes Dutch words from markdown text.`
Sprint Type: `module`
Module: `extract_words_from_text`
Status: `done`
---

## Goal

Replace the legacy `extract_words_from_text` function (a regex stub) with a production-quality `WordExtractor` class that uses LangChain tool calling to extract and normalize Dutch words from markdown text. The module must return `list[WordEntry]` with language-specific normalization (de/het articles for nouns, infinitive forms for verbs) and flat word-type assignment. All 3 test levels (unit, integration, e2e) must pass.

## Module Scope

### What this sprint implements
- Module: `extract_words_from_text`
- Architecture spec: `nl_processing/extract_words_from_text/docs/architecture_extract_words_from_text.md`
- PRD: `nl_processing/extract_words_from_text/docs/prd_extract_words_from_text.md`
- Epics reference: `docs/planning-artifacts/epics.md` — Epic 3

### Boundary Rules (STRICTLY ENFORCED)

**ALLOWED — this sprint may ONLY touch:**
- `nl_processing/extract_words_from_text/service.py` — replace legacy stub with `WordExtractor` class
- `nl_processing/extract_words_from_text/prompts/` — create directory, prompt generation script, prompt JSON
- `tests/unit/extract_words_from_text/` — unit tests (create conftest.py, test files)
- `tests/integration/extract_words_from_text/` — integration tests (create directory and test files)
- `tests/e2e/extract_words_from_text/` — e2e tests (create directory and test files)
- `vulture_whitelist.py` — update stale `extract_words_from_text` reference

**FORBIDDEN — this sprint must NEVER touch:**
- `nl_processing/core/` — core package (fully implemented)
- `nl_processing/extract_text_from_image/` — different module
- `nl_processing/translate_text/` — different module
- `nl_processing/translate_word/` — different module
- `nl_processing/database/` — different module
- `tests/unit/core/`, `tests/unit/extract_text_from_image/` — other module tests
- `tests/integration/core/`, `tests/integration/extract_text_from_image/` — other module tests
- `tests/e2e/extract_text_from_image/` — other module tests
- Any bot code
- `pyproject.toml`, `Makefile`, `ruff.toml`, `pytest.ini` — project-level config

### Test Scope
- **Unit test directory**: `tests/unit/extract_words_from_text/`
- **Unit test command**: `uv run pytest tests/unit/extract_words_from_text/ -x -v`
- **Integration test directory**: `tests/integration/extract_words_from_text/`
- **Integration test command**: `doppler run -- uv run pytest tests/integration/extract_words_from_text/ -x -v`
- **E2e test directory**: `tests/e2e/extract_words_from_text/`
- **E2e test command**: `doppler run -- uv run pytest tests/e2e/extract_words_from_text/ -x -v`
- **NEVER run**: `uv run pytest` (full suite) or tests from other modules

## Interface Contract

### Public interface this sprint implements

```python
from nl_processing.extract_words_from_text.service import WordExtractor
from nl_processing.core.models import Language, WordEntry

extractor = WordExtractor()  # defaults: language=Language.NL, model="gpt-4.1-mini"
words: list[WordEntry] = await extractor.extract(text)
```

- Constructor: `__init__(self, *, language: Language = Language.NL, model: str = "gpt-4.1-mini") -> None`
- Method: `async extract(self, text: str) -> list[WordEntry]`
- Returns empty `list[WordEntry]` for non-target language text (no exception)
- Raises `APIError` for upstream API failures

## Scope

### In
- Prompt generation script (`generate_nl_prompt.py`) + Dutch prompt JSON (`nl.json`)
- `WordExtractor` class in `service.py` (replacing the legacy `extract_words_from_text` function)
- Unit tests with mocked chain
- Integration tests with real API calls (5 curated test cases + performance test)
- E2e tests with full extraction scenarios
- Vulture whitelist update (replace legacy function reference with new class)

### Out
- Support for languages other than Dutch
- Deduplication or ordering guarantees
- Any changes to core models or exceptions
- Any changes to other modules

## Inputs (contracts)

- Requirements: `nl_processing/extract_words_from_text/docs/prd_extract_words_from_text.md`
- Architecture: `nl_processing/extract_words_from_text/docs/architecture_extract_words_from_text.md`
- Shared architecture: `docs/planning-artifacts/architecture.md`
- Shared PRD: `docs/planning-artifacts/prd.md`
- Epics: `docs/planning-artifacts/epics.md` — Epic 3
- Reference implementation: `nl_processing/extract_text_from_image/service.py`

## Change digest

- **Requirement deltas**: No changes to requirements. Implementing EWT-FR1 through EWT-FR14 and EWT-NFR1 through EWT-NFR2 from scratch.
- **Architecture deltas**: No changes to architecture. Following shared patterns from the reference implementation.

## Task list (dependency-aware)

- **T1:** `TASK_prompt_generation.md` (depends: --) (parallel: no) -- Create prompt generation script and Dutch prompt JSON
- **T2:** `TASK_service_implementation.md` (depends: T1) (parallel: no) -- Implement WordExtractor class, replacing legacy stub
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

- **Production database**: N/A -- this module has no database interactions.
- **Shared resource isolation**: N/A -- this module uses only OpenAI API calls, no local resources shared with production.
- **Migration deliverable**: N/A -- no data model changes.

## Definition of Done (DoD)

All items must be true:

- All tasks completed and verified
- Unit tests pass: `uv run pytest tests/unit/extract_words_from_text/ -x -v`
- Integration tests pass: `doppler run -- uv run pytest tests/integration/extract_words_from_text/ -x -v`
- E2e tests pass: `doppler run -- uv run pytest tests/e2e/extract_words_from_text/ -x -v`
- Module isolation: no files outside the ALLOWED list were touched
- Public interface matches architecture spec exactly (`WordExtractor` class with `extract` method)
- Zero legacy tolerance: legacy `extract_words_from_text` function removed, vulture whitelist updated
- No errors are silenced (no swallowed exceptions)
- Requirements/architecture docs unchanged
- Production database untouched
- `make check` passes fully (ruff format, ruff check, pylint, vulture, jscpd, all tests)

## Risks + mitigations

- **Risk**: LLM output variability may cause set-based tests to fail intermittently.
  - **Mitigation**: Use unambiguous, curated test cases. Use set comparison (normalized_form + word_type), not ordering. Pin model version.
- **Risk**: Prompt quality may not achieve 100% accuracy on first attempt.
  - **Mitigation**: Iterate on prompt few-shot examples using integration test feedback. Start with GPT-4.1-mini as baseline.
- **Risk**: Legacy stub function is referenced in vulture whitelist and potentially elsewhere.
  - **Mitigation**: T6 explicitly handles whitelist cleanup. Search for all legacy references.

## Migration plan (if data model changes)

N/A -- no data model changes.

## Rollback / recovery notes

- Revert all files in the ALLOWED list to their previous state (git checkout)
- The legacy stub in `service.py` is the only file being replaced

## Task validation status

- Per-task validation order: `T1` -> `T2` -> `T3` -> `T4` -> `T5` -> `T6`
- Validator: `self-validated`
- Outcome: `approved`

## Sources used

- Requirements: `nl_processing/extract_words_from_text/docs/prd_extract_words_from_text.md`
- Architecture: `nl_processing/extract_words_from_text/docs/architecture_extract_words_from_text.md`
- Shared architecture: `docs/planning-artifacts/architecture.md`
- Shared PRD: `docs/planning-artifacts/prd.md`
- Epics: `docs/planning-artifacts/epics.md`
- Code read: `nl_processing/extract_text_from_image/service.py`, `nl_processing/extract_text_from_image/prompts/generate_nl_prompt.py`, `nl_processing/extract_words_from_text/service.py` (legacy stub), `vulture_whitelist.py`, `nl_processing/core/models.py`, `nl_processing/core/exceptions.py`, `nl_processing/core/prompts.py`, `tests/unit/extract_text_from_image/`, `tests/integration/extract_text_from_image/`, `tests/e2e/extract_text_from_image/`

## Contract summary

### What (requirements)
- EWT-FR1-14: Extract and normalize Dutch words from markdown text with flat word-type taxonomy
- EWT-NFR1-2: <5s for ~100 words, no unnecessary processing

### How (architecture)
- `WordExtractor` class in `service.py` using LangChain `ChatOpenAI.bind_tools([WordEntry])` + `tool_calls` parsing
- Language-specific prompt JSON loaded via `core.prompts.load_prompt()`
- Flat word-type strings, language-specific normalization via prompt only
- Empty list for non-target language, `APIError` wrapping for upstream failures

## Impact inventory (implementation-facing)

- **Module**: `extract_words_from_text` (`nl_processing/extract_words_from_text/`)
- **Interfaces**: `WordExtractor.extract(text: str) -> list[WordEntry]`
- **Data model**: Uses `WordEntry` from `core` (already defined)
- **External services**: OpenAI API via LangChain
- **Test directories**: `tests/unit/extract_words_from_text/`, `tests/integration/extract_words_from_text/`, `tests/e2e/extract_words_from_text/`
