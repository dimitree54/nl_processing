---
Sprint ID: `2026-03-03_extract-text-v2-modifications`
Sprint Goal: `Fix make check failures, migrate to LangChain native prompt serialization, add few-shot examples, add multi-language integration tests`
Sprint Type: `module`
Module: `extract_text_from_image` (+ `core` for prompt loading changes)
Status: `planning`
Owners: `Developer`
---

## Goal

Apply four targeted modifications to the existing, working `extract_text_from_image` module: (1) fix `make check` failures from banned `unittest.mock.AsyncMock` imports, (2) migrate prompt serialization to LangChain native `dumpd()`/`load()`, (3) add 3-shot few-shot examples to the Dutch extraction prompt, (4) add multi-language integration tests. The module is already functional — these are improvements, not a rewrite.

## Module Scope

### What this sprint modifies

- Module: `extract_text_from_image` — prompt file, optional service.py adjustment, prompt generation script
- Core: `core/prompts.py` — replace custom JSON parsing with `langchain_core.load.load()`
- Core: `core/scripts/prompt_author.py` — replace custom serialization with `langchain_core.load.dumpd()`
- Unit tests: `tests/unit/extract_text_from_image/` — fix banned imports
- Unit tests: `tests/unit/core/test_prompts.py` — update for new prompt format
- Integration tests: `tests/integration/extract_text_from_image/` — add multi-language tests

### Boundary Rules (STRICTLY ENFORCED)

**ALLOWED — this sprint may ONLY touch:**
- `nl_processing/core/prompts.py` — rewrite prompt loading to use `langchain_core.load.load()`
- `nl_processing/core/scripts/prompt_author.py` — rewrite to use `langchain_core.load.dumpd()`
- `nl_processing/extract_text_from_image/prompts/nl.json` — regenerate in LangChain native format
- `nl_processing/extract_text_from_image/prompts/generate_nl_prompt.py` — new: script to generate nl.json with few-shot examples
- `nl_processing/extract_text_from_image/service.py` — minor adjustments if prompt loading interface changes
- `tests/unit/extract_text_from_image/test_extract_text_from_image.py` — fix banned import
- `tests/unit/extract_text_from_image/test_error_handling.py` — fix banned import
- `tests/unit/core/test_prompts.py` — update for new prompt format
- `tests/integration/extract_text_from_image/test_extraction_accuracy.py` — add multi-language tests

**FORBIDDEN — this sprint must NEVER touch:**
- Any other module's code or tests (`extract_words_from_text`, `translate_text`, `translate_word`)
- `nl_processing/core/models.py`, `nl_processing/core/exceptions.py`
- Bot code, database code
- `Makefile`, `ruff.toml`, `pyproject.toml`
- Requirements or architecture documentation

### Test Scope

- **Unit test commands:**
  - `uv run pytest tests/unit/extract_text_from_image/ -x -v`
  - `uv run pytest tests/unit/core/ -x -v`
- **Integration test command:** `doppler run -- uv run pytest tests/integration/extract_text_from_image/ -x -v`
- **Full check:** `doppler run -- make check` (final validation only)

## Interface Contract

### Public interface (unchanged)

```python
class ImageTextExtractor:
    def __init__(self, *, language: Language = Language.NL, model: str = "gpt-4.1-mini",
                 reasoning_effort: str | None = None, service_tier: str | None = None) -> None: ...
    async def extract_from_path(self, path: str) -> str: ...
    async def extract_from_cv2(self, image: numpy.ndarray) -> str: ...
```

### Core interface (modified)

```python
# nl_processing/core/prompts.py — signature stays the same, implementation changes
def load_prompt(prompt_path: str) -> ChatPromptTemplate: ...
```

## Scope

### In

- Fix `from unittest.mock import AsyncMock` in 2 test files (ruff TID251 ban)
- Migrate `core/prompts.py` to use `langchain_core.load.load()` deserialization
- Migrate `core/scripts/prompt_author.py` to use `langchain_core.load.dumpd()` serialization
- Regenerate `nl.json` in LangChain native format with 3 few-shot examples
- Create prompt generation script for reproducible nl.json generation
- Update `tests/unit/core/test_prompts.py` for new format
- Add integration tests for mixed-language and English-only images

### Out

- No changes to public API surface of `ImageTextExtractor`
- No new languages (only Dutch)
- No changes to `benchmark.py`, `image_encoding.py`
- No changes to `core/models.py`, `core/exceptions.py`
- No Makefile, ruff.toml, or pyproject.toml changes

## Inputs (contracts)

- Requirements: `nl_processing/extract_text_from_image/docs/prd_extract_text_from_image.md` (FR3, FR4, FR7)
- Architecture: `docs/planning-artifacts/architecture.md` (CFR13 — LangChain native prompt format)
- Architecture: `nl_processing/extract_text_from_image/docs/architecture_extract_text_from_image.md`
- Lint config: `ruff.toml` (TID251 — `unittest.mock` ban)

## Change digest

- **Requirement deltas**: None. All modifications fulfill existing requirements (CFR13, FR3, FR4).
- **Architecture deltas**: None. The architecture already mandates LangChain native serialization — the current code is non-compliant and this sprint corrects it.

## Task list (dependency-aware)

- **T1:** `TASK_01_fix_unittest_mock_ban.md` (depends: —) (parallel: no) — Fix banned `unittest.mock.AsyncMock` imports in 2 test files
- **T2:** `TASK_02_migrate_prompt_serialization.md` (depends: T1) (parallel: no) — Migrate core prompt loading/saving to LangChain native `dumpd()`/`load()`
- **T3:** `TASK_03_generate_fewshot_prompt.md` (depends: T2) (parallel: no) — Create prompt generation script with 3 few-shot examples, regenerate `nl.json`
- **T4:** `TASK_04_verify_module_integration.md` (depends: T3) (parallel: no) — Verify service.py works with new prompt, fix if needed, run full unit test suite
- **T5:** `TASK_05_add_multilanguage_integration_tests.md` (depends: T4) (parallel: no) — Add mixed-language and English-only integration tests

## Dependency graph (DAG)

- T1 → T2 → T3 → T4 → T5

## Execution plan

### Critical path

T1 → T2 → T3 → T4 → T5

### Parallel tracks (lanes)

None — all tasks are sequential. Each task modifies files or depends on outputs from the previous task.

## Production safety

The current application version is **running in production on this same machine** (different directory).

- **Production database**: N/A — no database operations in this sprint.
- **Shared resource isolation**: No ports, sockets, or shared files. Only file-path-based prompt JSON changes, which are internal to the module directory.
- **Migration deliverable**: N/A — no data model changes.

## Definition of Done (DoD)

All items must be true:

- ✅ All tasks completed and verified
- ✅ `from unittest.mock import AsyncMock` removed from both test files
- ✅ `core/prompts.py` uses `langchain_core.load.load()` — no custom parsing
- ✅ `core/scripts/prompt_author.py` uses `langchain_core.load.dumpd()` — no custom serialization
- ✅ `nl.json` is in LangChain native format with 3 few-shot examples
- ✅ `nl.json` is generated by a script (not hand-written)
- ✅ Unit tests pass: `uv run pytest tests/unit/extract_text_from_image/ -x -v`
- ✅ Unit tests pass: `uv run pytest tests/unit/core/ -x -v`
- ✅ Integration tests pass: `doppler run -- uv run pytest tests/integration/extract_text_from_image/ -x -v`
- ✅ `doppler run -- make check` passes
- ✅ Public interface unchanged — `ImageTextExtractor` API is identical
- ✅ Zero legacy tolerance — old custom prompt format code removed, not left alongside new
- ✅ No errors are silenced
- ✅ Module isolation maintained — no other modules touched

## Risks + mitigations

- **Risk**: `langchain_core.load.load()` is marked beta and may change API.
  - **Mitigation**: Pin `langchain>=0.3,<1` (already pinned in pyproject.toml). The `load()` function has been stable since langchain-core 0.2. If it changes, the error will be caught by tests immediately.

- **Risk**: `dumpd()`/`load()` round-trip may not preserve `MessagesPlaceholder` or `AIMessage.tool_calls` correctly.
  - **Mitigation**: Verified manually — round-trip works for SystemMessage, HumanMessage with image_url content, AIMessage with tool_calls, and MessagesPlaceholder. Test coverage will confirm.

- **Risk**: Few-shot example images embedded in nl.json will significantly increase file size.
  - **Mitigation**: Generated synthetic images are small (800x200 white background with text, ~2-5KB as base64). Total file size will be manageable. The file is loaded once at constructor time.

- **Risk**: Removing `AsyncMock` from tests without `pytest-mock` (not installed).
  - **Mitigation**: Replace with plain `async def` mock functions + `SimpleNamespace` objects for return values. The existing test pattern already uses `SimpleNamespace` for responses — only the chain mock needs to change.

## Migration plan (if data model changes)

N/A — no data model changes.

## Rollback / recovery notes

- Revert all changes via `git revert`. The module was working before; all changes are additive or replacement (no schema migration).

## Task validation status

- Per-task validation order: `T1` → `T2` → `T3` → `T4` → `T5`
- Validator: `self-validated`
- Outcome: `approved`

## Sources used

- Requirements: `nl_processing/extract_text_from_image/docs/prd_extract_text_from_image.md`
- Architecture: `docs/planning-artifacts/architecture.md`
- Module architecture: `nl_processing/extract_text_from_image/docs/architecture_extract_text_from_image.md`
- Code read: `nl_processing/core/prompts.py`, `nl_processing/core/scripts/prompt_author.py`, `nl_processing/extract_text_from_image/service.py`, `nl_processing/extract_text_from_image/prompts/nl.json`, `nl_processing/extract_text_from_image/benchmark.py`, `nl_processing/extract_text_from_image/image_encoding.py`, `nl_processing/core/models.py`, `nl_processing/core/exceptions.py`
- Tests read: `tests/unit/extract_text_from_image/test_extract_text_from_image.py`, `tests/unit/extract_text_from_image/test_error_handling.py`, `tests/unit/core/test_prompts.py`, `tests/integration/extract_text_from_image/test_extraction_accuracy.py`
- Config read: `ruff.toml`, `Makefile`, `pyproject.toml`, `vulture_whitelist.py`

## Contract summary

### What (requirements)

- CFR13: Prompt JSON files must use LangChain native `ChatPromptTemplate` serialization (not custom format)
- FR3/FR4: Module extracts only target language text, ignores other languages
- FR7: Module raises `TargetLanguageNotFoundError` when no target language text found
- TID251: No `unittest` imports (ruff ban)

### How (architecture)

- `core/prompts.py` → `langchain_core.load.load()` for deserialization
- `core/scripts/prompt_author.py` → `langchain_core.load.dumpd()` for serialization
- Few-shot examples: SystemMessage + 3×(HumanMessage[image] + AIMessage[tool_call]) + MessagesPlaceholder
- Tests: async mock via plain `async def` functions (no `unittest.mock`)

## Impact inventory (implementation-facing)

- **Module**: `extract_text_from_image` — `nl_processing/extract_text_from_image/`
- **Core**: `nl_processing/core/prompts.py`, `nl_processing/core/scripts/prompt_author.py`
- **Interfaces**: `load_prompt()` signature unchanged, return type unchanged
- **Data model**: No changes
- **External services**: OpenAI API (existing, no new integrations)
- **Test directories**: `tests/unit/extract_text_from_image/`, `tests/unit/core/`, `tests/integration/extract_text_from_image/`
