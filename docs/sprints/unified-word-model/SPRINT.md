---
Sprint ID: 2026-03-04_unified-word-model
Sprint Goal: Replace WordEntry and TranslationResult with a unified Word model backed by PartOfSpeech Enum
Sprint Type: refactoring
Module: core + extract_words_from_text + translate_word
Status: planning
---

## Goal

Replace the separate `WordEntry` and `TranslationResult` models with a single unified `Word` model. Introduce a `PartOfSpeech` Enum to replace the stringly-typed `word_type` field. This is done incrementally: add new models alongside old ones, migrate modules one by one, then remove the old models and update documentation.

## Module Scope

### What this sprint implements

- **core**: Add `PartOfSpeech` Enum and `Word` model; eventually remove `WordEntry` and `TranslationResult`
- **extract_words_from_text**: Migrate from `WordEntry` to `Word`
- **translate_word**: Migrate from `TranslationResult` to `Word`; change input from `list[str]` to `list[Word]`; change output from `list[TranslationResult]` to `list[Word]`
- **Documentation**: Update all architecture and PRD docs to reflect the new model

### Boundary Rules (STRICTLY ENFORCED)

**ALLOWED -- this sprint may ONLY touch:**

Source code:
- `nl_processing/core/models.py`
- `nl_processing/extract_words_from_text/service.py`
- `nl_processing/extract_words_from_text/prompts/generate_nl_prompt.py`
- `nl_processing/extract_words_from_text/prompts/nl.json` (regenerated)
- `nl_processing/translate_word/service.py`
- `nl_processing/translate_word/prompts/generate_nl_ru_prompt.py`
- `nl_processing/translate_word/prompts/nl_ru.json` (regenerated)
- `vulture_whitelist.py` (if needed)

Tests:
- `tests/unit/core/test_models.py`
- `tests/unit/extract_words_from_text/test_word_extractor.py`
- `tests/unit/extract_words_from_text/conftest.py`
- `tests/unit/extract_words_from_text/test_error_handling.py`
- `tests/unit/translate_word/test_word_translator.py`
- `tests/unit/translate_word/conftest.py`
- `tests/unit/translate_word/test_error_handling.py`
- `tests/integration/extract_words_from_text/test_extraction_accuracy.py`
- `tests/integration/translate_word/test_translation_accuracy.py`
- `tests/e2e/extract_words_from_text/test_full_extraction.py`
- `tests/e2e/extract_words_from_text/test_real_text_quality.py`
- `tests/e2e/translate_word/test_full_translation.py`
- `tests/e2e/translate_word/test_product_box_quality.py`

Documentation (Task 5 only):
- `docs/planning-artifacts/architecture.md`
- `nl_processing/extract_words_from_text/docs/architecture_extract_words_from_text.md`
- `nl_processing/extract_words_from_text/docs/prd_extract_words_from_text.md`
- `nl_processing/translate_word/docs/architecture_translate_word.md`
- `nl_processing/translate_word/docs/prd_translate_word.md`

**FORBIDDEN -- this sprint must NEVER touch:**
- `nl_processing/translate_text/` (all files)
- `nl_processing/extract_text_from_image/` (all files)
- `nl_processing/database/` (all files)
- `nl_processing/core/exceptions.py`
- `nl_processing/core/prompts.py`
- `nl_processing/core/scripts/prompt_author.py`
- Any test files not listed above
- Any `.md` files outside `docs/sprints/unified-word-model/` and the documentation files listed above (Task 5 only)
- Creating any new files not listed above

### Test Commands (per task)

| Task | Command |
|------|---------|
| T1 | `uv run pytest tests/unit/core/ -x -v` |
| T2 | `uv run pytest tests/unit/core/ tests/unit/extract_words_from_text/ -x -v` then `doppler run -- uv run pytest tests/integration/extract_words_from_text/ tests/e2e/extract_words_from_text/ -x -v` |
| T3 | `uv run pytest tests/unit/core/ tests/unit/translate_word/ -x -v` then `doppler run -- uv run pytest tests/integration/translate_word/ tests/e2e/translate_word/ -x -v` |
| T4 | `uv run pytest tests/unit/core/ -x -v` |
| T5 | No code tests -- doc review only |
| Final | `make check` |

## Interface Contract

### Current public interfaces (BEFORE this sprint)

```python
# core/models.py
class WordEntry(BaseModel):
    normalized_form: str
    word_type: str

class TranslationResult(BaseModel):
    translation: str
```

```python
# extract_words_from_text/service.py
class WordExtractor:
    async def extract(self, text: str) -> list[WordEntry]: ...
```

```python
# translate_word/service.py
class WordTranslator:
    async def translate(self, words: list[str]) -> list[TranslationResult]: ...
```

### Target public interfaces (AFTER this sprint)

```python
# core/models.py
class PartOfSpeech(Enum):
    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    PREPOSITION = "preposition"
    CONJUNCTION = "conjunction"
    PRONOUN = "pronoun"
    ARTICLE = "article"
    NUMERAL = "numeral"
    PROPER_NOUN_PERSON = "proper_noun_person"
    PROPER_NOUN_COUNTRY = "proper_noun_country"

class Word(BaseModel):
    normalized_form: str
    word_type: PartOfSpeech
    language: Language
```

```python
# extract_words_from_text/service.py
class WordExtractor:
    async def extract(self, text: str) -> list[Word]: ...
```

```python
# translate_word/service.py
class WordTranslator:
    async def translate(self, words: list[Word]) -> list[Word]: ...
```

## Scope

### In
- `PartOfSpeech` Enum with 11 values
- Unified `Word` model replacing both `WordEntry` and `TranslationResult`
- Migration of `extract_words_from_text` module to use `Word`
- Migration of `translate_word` module to use `Word` (input and output)
- Updated few-shot examples in both prompt generators
- Regenerated prompt JSON files
- Removal of deprecated `WordEntry` and `TranslationResult` models
- Updated documentation (architecture + PRDs)

### Out
- No changes to `translate_text` module
- No changes to `extract_text_from_image` module
- No changes to `database` module
- No new language support
- No new features beyond model unification

## Inputs (contracts)

- Architecture: `docs/planning-artifacts/architecture.md` -- defines `WordEntry`, `TranslationResult`, module interfaces
- Module architecture: `nl_processing/extract_words_from_text/docs/architecture_extract_words_from_text.md`
- Module architecture: `nl_processing/translate_word/docs/architecture_translate_word.md`
- Module PRDs: `nl_processing/extract_words_from_text/docs/prd_extract_words_from_text.md`, `nl_processing/translate_word/docs/prd_translate_word.md`
- Current codebase: all source files listed in ALLOWED section

## Change digest

- **Requirement deltas**: `WordEntry` and `TranslationResult` are being replaced by a single `Word` model. `word_type` changes from `str` to `PartOfSpeech` Enum. `translate_word` input changes from `list[str]` to `list[Word]`.
- **Architecture deltas**: Core models simplify from 3 public models (`ExtractedText`, `WordEntry`, `TranslationResult`) to 2 (`ExtractedText`, `Word`) plus a new `PartOfSpeech` Enum. The data flow changes: `extract_words_from_text` now outputs `list[Word]` which feeds directly into `translate_word` as `list[Word]`.

## Task list (dependency-aware)

**Rule**: Every task has its own `TASK_*.md` file. No task bodies are inlined here.

- **T1:** [`TASK_01.md`](TASK_01.md) (depends: --) -- Add PartOfSpeech Enum and Word model to core (alongside existing models)
- **T2:** [`TASK_02.md`](TASK_02.md) (depends: T1) -- Migrate extract_words_from_text to use Word model
- **T3:** [`TASK_03.md`](TASK_03.md) (depends: T2) -- Migrate translate_word to use Word model
- **T4:** [`TASK_04.md`](TASK_04.md) (depends: T3) -- Remove deprecated WordEntry and TranslationResult from core
- **T5:** [`TASK_05.md`](TASK_05.md) (depends: T4) -- Update documentation to reflect unified Word model

## Dependency graph (DAG)

```
T1 --> T2 --> T3 --> T4 --> T5
```

Strictly sequential. Each task depends on the one before it.

## Execution plan

### Critical path

T1 --> T2 --> T3 --> T4 --> T5

### Parallel tracks (lanes)

None. All tasks are sequential -- each builds on the previous migration step.

## Production safety

The current application version is **running in production on this same machine** (different directory).

- **Production database**: NOT modified during this sprint. This sprint changes only models, services, prompts, and tests. No database operations.
- **Shared resource isolation**: N/A -- this sprint does not use ports, sockets, temp dirs, or file-based resources that could collide with production. Integration/e2e tests make OpenAI API calls but do not share state with production.
- **Migration deliverable**: N/A -- no data model changes that affect persistent storage.

## Definition of Done (DoD)

All items must be true:

- [ ] All 5 tasks completed and verified
- [ ] `WordEntry` and `TranslationResult` models removed from `core/models.py`
- [ ] `PartOfSpeech` Enum and `Word` model exist in `core/models.py`
- [ ] `extract_words_from_text` returns `list[Word]`
- [ ] `translate_word` accepts `list[Word]` and returns `list[Word]`
- [ ] All few-shot examples updated in prompt generators
- [ ] All prompt JSON files regenerated
- [ ] `make check` passes 100% green (unit + integration + e2e)
- [ ] No quality regression in LLM tests (same accuracy thresholds as before)
- [ ] Module isolation: no files outside the ALLOWED list were touched
- [ ] Zero legacy: no dead code, no unused imports, no stale references
- [ ] All documentation updated (architecture, PRDs)
- [ ] Vulture whitelist updated if needed

## Risks + mitigations

- **Risk**: LLM quality regression after prompt changes (new few-shot format)
  - **Mitigation**: Integration and e2e tests use the same exact accuracy thresholds. If they fail, STOP and report to user. Do not loosen gates.

- **Risk**: `PartOfSpeech` Enum is too restrictive for some LLM outputs
  - **Mitigation**: The Enum covers all word types currently used in prompts and tests. Pydantic will raise a validation error on unknown values, which surfaces the problem immediately rather than silently.

- **Risk**: Changing `translate_word` input from `list[str]` to `list[Word]` breaks callers
  - **Mitigation**: Zero-legacy policy -- callers must update. This sprint updates all known tests and callers within the project. External callers (if any) are a user responsibility.

## Rollback / recovery notes

- Each task is a discrete commit. Reverting to pre-sprint state means reverting all 5 commits.
- Tasks are designed to be safe at each boundary: after T1, old code still works. After T2, `extract_words_from_text` works with `Word`. After T3, `translate_word` works with `Word`. After T4, legacy models are gone. T5 is documentation only.

## Task validation status

- Per-task validation order: T1 --> T2 --> T3 --> T4 --> T5
- Outcome: planned

## Sources used

- Architecture: `docs/planning-artifacts/architecture.md`
- Module architecture: `nl_processing/extract_words_from_text/docs/architecture_extract_words_from_text.md`
- Module architecture: `nl_processing/translate_word/docs/architecture_translate_word.md`
- Module PRD: `nl_processing/extract_words_from_text/docs/prd_extract_words_from_text.md`
- Module PRD: `nl_processing/translate_word/docs/prd_translate_word.md`
- Code read: `nl_processing/core/models.py`, `nl_processing/core/exceptions.py`, `nl_processing/core/prompts.py`, `nl_processing/core/scripts/prompt_author.py`
- Code read: `nl_processing/extract_words_from_text/service.py`, `nl_processing/extract_words_from_text/prompts/generate_nl_prompt.py`
- Code read: `nl_processing/translate_word/service.py`, `nl_processing/translate_word/prompts/generate_nl_ru_prompt.py`
- Code read: All test files listed in ALLOWED section
- Code read: `tests/conftest.py` (shared test helpers)
- Code read: `vulture_whitelist.py`, `Makefile`

## Contract summary

### What (requirements)
- Replace `WordEntry(normalized_form: str, word_type: str)` with `Word(normalized_form: str, word_type: PartOfSpeech, language: Language)`
- Replace `TranslationResult(translation: str)` with `Word` (same model, `language=Language.RU`)
- Change `translate_word` input from `list[str]` to `list[Word]`
- LLM returns `{normalized_form, word_type}` -- service adds `language` programmatically
- `PartOfSpeech` Enum is extensible for future language-specific values

### How (architecture)
- Incremental migration: add new models first, migrate modules one by one, remove old models last
- Internal Pydantic models for LLM tool calling (`_LLMWordEntry`, `_LLMTranslationEntry`) stay separate from public `Word` model -- LLM should not set `language`
- Few-shot examples in prompt generators updated to use new format
- Prompt JSON files regenerated after generator changes

## Impact inventory (implementation-facing)

- **Module**: `core` (`nl_processing/core/models.py`)
- **Module**: `extract_words_from_text` (`nl_processing/extract_words_from_text/service.py`, prompts)
- **Module**: `translate_word` (`nl_processing/translate_word/service.py`, prompts)
- **Interfaces**: `WordExtractor.extract()`, `WordTranslator.translate()`
- **Data model**: `Word`, `PartOfSpeech` (new); `WordEntry`, `TranslationResult` (removed)
- **External services**: OpenAI API via LangChain (unchanged, but prompts updated)
- **Test directories**: `tests/unit/core/`, `tests/unit/extract_words_from_text/`, `tests/unit/translate_word/`, `tests/integration/extract_words_from_text/`, `tests/integration/translate_word/`, `tests/e2e/extract_words_from_text/`, `tests/e2e/translate_word/`
