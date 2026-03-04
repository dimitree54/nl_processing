---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-02b-vision', 'step-02c-executive-summary', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
inputDocuments: ['product-brief-database-2026-03-02.md']
parentPrd: docs/planning-artifacts/prd.md
workflowType: 'prd'
classification:
  projectType: developer_tool
  domain: scientific
  complexity: medium
  projectContext: greenfield
---

# Product Requirements Document - database

**Author:** Dima
**Date:** 2026-03-02

> For shared requirements (structured output, configuration, language support, error handling, NFRs), see the [shared PRD](../../../docs/planning-artifacts/prd.md). This document covers only module-specific requirements.

## Executive Summary

`database` is an async persistence module that stores, links, and retrieves words across multiple languages using a shared relational database (Neon PostgreSQL). It manages per-language word tables, per-language-pair translation link tables, and per-user word lists. The developer instantiates `DatabaseService` with a `user_id`, then calls async methods to add words and retrieve word-translation pairs. New words trigger automatic asynchronous translation via direct integration with `translate_word`. The module requires database connection environment variables — no defaults, fails fast with setup instructions if missing.

### What Makes This Special

- **Symmetric multilingual persistence** with no privileged language — each language has its own table, translation links are per-pair
- **Fire-and-forget translation** — add_words returns immediately, translation happens asynchronously
- **Growing shared corpus** — the more users add words, the richer the shared vocabulary; translations are paid for once globally
- **Hard 200ms latency contract** enforced during development, not as an afterthought

## Success Criteria

### Technical Success

- All database operations (add/check/get) complete within ≤200ms against Neon PostgreSQL
- Words are never duplicated in shared tables — deduplication is correct
- Translation links correctly associate words across language tables
- User word lists accurately reference the shared corpus
- Async translation fires without blocking add_words return
- get_words excludes untranslated words with a logged warning
- Module fails fast with clear setup instructions when environment variables are missing

### Measurable Outcomes

| Metric | Target | Measurement |
|---|---|---|
| Add/check latency | ≤ 200ms per operation | Benchmark timing against Neon |
| Deduplication correctness | 100% — no duplicate words | Integration test assertions |
| Translation link accuracy | 100% — correct word associations | Integration test assertions |
| Async translation | Non-blocking return | Timing test: add_words returns before translation completes |
| Integration time | Minutes | Docstring completeness |

## Scope

All features are required — no phased MVP. The module either works completely or is not ready.

**Risk Mitigation:**
- **Technical (latency):** Hard 200ms ceiling. If Neon PostgreSQL exceeds this during development — stop, report to Dima, and evaluate alternative backends. The abstract backend interface makes switching feasible.
- **Technical (async):** Fire-and-forget translation must not leak exceptions or block the caller. Errors in translation are logged, not raised.
- **Resource:** Single-developer module — low risk given clear scope.

**Growth (Post-Release):**
- Additional language tables and translation link tables as the project expands
- More sophisticated caching and query capabilities

## User Journeys

### Journey 1: First Integration (Happy Path)

**Alex, backend developer**, has a working pipeline that extracts Dutch words from text using `extract_words_from_text`. Now he wants to persist those words and get translations.

**Opening Scene:** Alex finds `database` in the nl_processing project. Reads the docstring — set database environment variables, instantiate `DatabaseService` with user_id, call `add_words()`. Four lines of code.

**Rising Action:** Alex sets `DATABASE_URL` in his environment (Neon connection string). Creates tables with `create_tables()`. Instantiates `DatabaseService("alex")`. Calls `add_words(dutch_words)` with `list[Word]` objects from the extraction pipeline — the same `Word` model that `extract_words_from_text` outputs. Gets immediate feedback as `AddWordsResult`: 8 words in `new_words`, 2 in `existing_words`.

**Climax:** Alex calls `get_words()` a few seconds later — gets back `list[WordPair]`, each containing a source `Word` (Dutch) and target `Word` (Russian). Some of the just-added words already have translations. Alex calls again later — all translations are complete.

**Resolution:** The module becomes a transparent persistence layer in Alex's pipeline. Words accumulate in the shared corpus. Each run only translates genuinely new words. Alex's vocabulary grows over time.

### Journey 2: Filtered Retrieval

**Alex** wants to study only nouns. He calls `get_words(word_type=PartOfSpeech.NOUN, limit=10, random=True)` — gets 10 random `WordPair` objects, each a Dutch noun `Word` paired with its Russian translation `Word`. Next day, he wants all verbs — `get_words(word_type=PartOfSpeech.VERB)`.

### Journey 3: Error Handling

**Alex** forgets to set `DATABASE_URL`. Instantiation raises `ConfigurationError` with a clear message: "DATABASE_URL environment variable is required. Set it to your Neon PostgreSQL connection string." Alex sets it, tries again — works.

Later, the Neon service is temporarily unavailable. `add_words()` raises `DatabaseError` with a clear message. Alex catches it, retries later.

### Journey Requirements Summary

| Capability | Revealed By |
|---|---|
| `DatabaseService` class with `user_id` constructor | Journey 1 |
| `create_tables()` convenience function | Journey 1 |
| `add_words()` with deduplication and immediate feedback | Journey 1 |
| Async translation via `translate_word` | Journey 1 |
| `get_words()` with word-translation pairs | Journey 1 |
| `get_words()` with filtering (word_type, limit, random) | Journey 2 |
| `ConfigurationError` for missing env vars | Journey 3 |
| `DatabaseError` for database failures | Journey 3 |

## Developer Tool Specific Requirements

### API Surface

**Public interface:**

```python
from nl_processing.database.service import DatabaseService
from nl_processing.core.models import Word, Language, PartOfSpeech

# One-time setup
await DatabaseService.create_tables()

# Per-user usage
db = DatabaseService(user_id="alex")

# add_words accepts list[Word] from core.models
words = [
    Word(normalized_form="de fiets", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="lopen", word_type=PartOfSpeech.VERB, language=Language.NL),
]
result = await db.add_words(words)
# result.new_words: list[Word] — newly added words
# result.existing_words: list[Word] — words already in the corpus

# get_words returns list[WordPair] — source Word + translated Word
pairs = await db.get_words(
    word_type=PartOfSpeech.NOUN,  # optional filter
    limit=10,                      # optional limit
    random=True,                   # optional random sampling
)
# pairs[0].source  → Word(normalized_form="de fiets", word_type=NOUN, language=NL)
# pairs[0].target  → Word(normalized_form="велосипед", word_type=NOUN, language=RU)
```

**Core model used:** `Word` from `nl_processing.core.models` — unified model with `normalized_form: str`, `word_type: PartOfSpeech`, `language: Language`. Same model used by `extract_words_from_text` (output) and `translate_word` (input/output). The `database` module stores and returns `Word` instances directly — no conversion needed between modules.

**Module-internal models** (in `database/models.py`):
- `AddWordsResult` — feedback from `add_words()`: `new_words: list[Word]`, `existing_words: list[Word]`
- `WordPair` — a source `Word` paired with its translated `Word`: `source: Word`, `target: Word`

**Constructor:**
- `user_id: str` — required, identifies the user
- `source_language: Language` — default: `Language.NL`
- `target_language: Language` — default: `Language.RU`

**Exceptions** (module-specific, not from `core`):
- `ConfigurationError` — missing or invalid environment variables, with setup instructions
- `DatabaseError` — database connectivity or operation failures

### Implementation Considerations

- All public methods accept and return `Word` instances from `core.models` — the `Word` model is the canonical data type for the entire pipeline
- `word_type` stored in DB as `PartOfSpeech.value` string (e.g., `"noun"`), reconstructed to enum on read
- `language` not stored in per-language word tables (redundant) — set programmatically on read based on table
- Direct dependency on `translate_word` for async translation of new words
- `asyncpg` for async PostgreSQL connectivity to Neon
- Abstract backend interface for future backend swaps
- Local caching layer for recently-accessed data
- Structured logging (Python `logging` module with console handler, Sentry-attachable)
- All public methods are `async`

## Functional Requirements

### Database Setup

- FR1: Module provides `create_tables()` async class method that creates all required tables (empty) in a single call
- FR2: Module creates per-language word tables (e.g., `words_nl`, `words_ru`) with columns: `id` (SERIAL PK), `normalized_form` (VARCHAR UNIQUE), `word_type` (VARCHAR) — mapped from `Word.normalized_form` and `Word.word_type.value`
- FR3: Module creates per-language-pair translation link tables (e.g., `translations_nl_ru`) referencing both language tables
- FR4: Module creates per-user word list tables referencing the shared language tables

### Word Management

- FR5: `add_words(words: list[Word])` accepts a list of `Word` objects (from `core.models`) and adds new words to the appropriate language table (determined by `Word.language`)
- FR6: Module checks for word existence by `normalized_form` before adding — duplicates are silently skipped
- FR7: `add_words()` returns `AddWordsResult` with `new_words: list[Word]` and `existing_words: list[Word]`
- FR8: `add_words()` records user-word associations for all provided words (new and existing)
- FR9: `add_words()` triggers asynchronous translation of new words via `translate_word` — does not wait for completion. Translated words are returned as `list[Word]` with `language` set to the target language.
- FR10: When async translation completes, the module stores translated `Word` objects in the target language table and creates translation link records

### Word Retrieval

- FR11: `get_words()` returns `list[WordPair]` — each containing a source `Word` and its translated `Word` (both from `core.models`)
- FR12: Words with pending translations (not yet completed) are excluded from results, with a warning logged
- FR13: `get_words()` accepts optional `word_type: PartOfSpeech` parameter to filter by part of speech
- FR14: `get_words()` accepts optional `limit: int` parameter to restrict result count
- FR15: `get_words()` accepts optional `random: bool` parameter for random sampling when combined with `limit`

### Configuration

- FR16: Module requires database connection via environment variables (e.g., `DATABASE_URL`)
- FR17: Module fails immediately at instantiation with `ConfigurationError` including setup instructions when required environment variables are missing
- FR18: Module accepts `source_language` and `target_language` in constructor (defaults: `Language.NL`, `Language.RU`)

### Logging

- FR19: Module uses structured logging abstraction — console output as initial backend
- FR20: Logging abstraction is designed for easy Sentry attachment without code changes
- FR21: Async translation failures are logged as warnings, not raised to the caller
- FR22: Untranslated words excluded from get_words are logged as warnings

### Testing Utilities

- FR23: Module provides a `drop_all_tables()` async function that drops all module-managed tables (word tables, link tables, user_words). Irreversible.
- FR24: Module provides a `reset_database()` async function that drops all tables and recreates them empty (equivalent to drop_all + create_tables)
- FR25: Module provides `count_words(table)`, `count_user_words(user_id, language)`, and `count_translation_links(table)` async helper functions for test assertions
- FR26: All testing utilities live in a separate `testing.py` file, clearly separated from production code — never imported by production modules
- FR27: `create_tables()` uses `IF NOT EXISTS` semantics — safe to call in any environment without risk of data loss

## Non-Functional Requirements (Module-Specific)

### Performance

- NFR1: Single word add/existence-check operation completes in ≤200ms against Neon PostgreSQL (wall clock time including network round-trip)
- NFR2: If 200ms threshold is exceeded during development — halt development and report to Dima for backend re-evaluation
- NFR3: Local caching layer reduces read latency for recently-accessed data
- NFR4: Batch operations (multiple words) should leverage database batch capabilities where possible

### Async

- NFR5: All public methods are async (`async def`)
- NFR6: Translation triggered by `add_words()` runs as a background task — does not block method return
- NFR7: Background task failures are logged, not raised to the caller

### Reliability

- NFR8: Database connection failures surface as `DatabaseError` with clear messages
- NFR9: Module handles connection pooling internally — caller does not manage connections

### Testing

- NFR10: E2e tests run against a real Neon database using `DATABASE_URL` from Doppler `dev` environment
- NFR11: E2e tests always start with `reset_database()` in setup and `drop_all_tables()` in teardown — dev database is always left clean
- NFR12: `stg` and `prd` Doppler environments point to stable Neon databases — never touched by automated tests
- NFR13: E2e tests exercise the full flow: table creation → word addition → async translation → user word retrieval → cleanup
- NFR14: Integration tests include a latency benchmark: p95 of add/check operations across 50 words must be ≤200ms

### Module-Specific Dependencies

- NFR15: `asyncpg` — async PostgreSQL driver for Neon connectivity
- NFR16: `translate_word` — direct dependency for automatic translation of new words
