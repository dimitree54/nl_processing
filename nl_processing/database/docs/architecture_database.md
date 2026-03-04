---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-03-02'
inputDocuments:
  - docs/planning-artifacts/product-brief.md
  - docs/planning-artifacts/prd.md
  - docs/planning-artifacts/architecture.md
  - nl_processing/database/docs/product-brief-database-2026-03-02.md
  - nl_processing/database/docs/prd_database.md
workflowType: 'architecture'
project_name: 'nl_processing'
user_name: 'Dima'
date: '2026-03-02'
scope: 'database'
parentArchitecture: docs/planning-artifacts/architecture.md
---

# Architecture Decision Document — database

> For shared architectural decisions (core package, code style, patterns, project structure), see the [shared architecture](../../../docs/planning-artifacts/architecture.md). This document covers only module-specific decisions.

---

## Core Data Model: `Word` from `core.models`

The `database` module persists and retrieves instances of the unified `Word` model defined in `nl_processing.core.models`:

```python
class Word(BaseModel):
    normalized_form: str
    word_type: PartOfSpeech    # enum: NOUN, VERB, ADJECTIVE, ADVERB, PREPOSITION, ...
    language: Language          # enum: NL, RU (extensible)
```

Supporting types (also from `core.models`):

```python
class Language(Enum):
    NL = "nl"
    RU = "ru"

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
```

### Model-to-Database Mapping

| `Word` field | DB column | Storage notes |
|---|---|---|
| `normalized_form` | `normalized_form` (VARCHAR, UNIQUE) | Direct mapping |
| `word_type` | `word_type` (VARCHAR) | Stored as `PartOfSpeech.value` string (e.g., `"noun"`, `"verb"`) |
| `language` | **Not stored as column** — determined by table | `words_nl` contains NL words, `words_ru` contains RU words. Redundant in DB. |

**Key design decisions:**

- **`language` is not a DB column** in per-language word tables. It would be redundant — the table itself defines the language. When reading from DB, `DatabaseService` reconstructs the full `Word` object by setting `language` programmatically based on which table was queried.
- **`word_type` is stored as the string value** of the `PartOfSpeech` enum (e.g., `"noun"`), not the enum name (e.g., `"NOUN"`). This keeps the DB human-readable and decoupled from Python enum naming.
- **`PartOfSpeech` is a closed enum** — adding a new part of speech requires updating the enum in `core.models`. This is an intentional trade-off: type safety and IDE autocompletion over runtime flexibility. The enum is designed to be extended as needed.

---

## Module-Specific Architectural Decisions

### Decision: Symmetric Per-Language Tables

Each language has its own word table (`words_nl`, `words_ru`, etc.) with identical schema. No language is treated as "source" or "target" at the table level — they are simply collections of words for that language.

**Rationale:** (1) Adding a new language is a table-creation task, not a schema change. (2) No implicit bias toward any language in the data model. (3) Translation links are a separate concern — language tables don't know they participate in translation.

**Table schema (per language):**

| Column | Type | Constraints | Maps to |
|---|---|---|---|
| `id` | SERIAL | PRIMARY KEY | (internal, not in `Word` model) |
| `normalized_form` | VARCHAR | NOT NULL, UNIQUE | `Word.normalized_form` |
| `word_type` | VARCHAR | NOT NULL | `Word.word_type.value` |

### Decision: Per-Language-Pair Translation Link Tables

Translation links are stored in separate tables per language pair (`translations_nl_ru`). Each row references one word from each language table.

**Rationale:** (1) Clean separation — each language pair has independent translation data. (2) No cross-contamination between language pairs. (3) Adding a new pair is a new table, not a schema change.

**Table schema (per language pair):**

| Column | Type | Constraints |
|---|---|---|
| `id` | SERIAL | PRIMARY KEY |
| `source_word_id` | INTEGER | FOREIGN KEY → source language table |
| `target_word_id` | INTEGER | FOREIGN KEY → target language table |
| | | UNIQUE(source_word_id, target_word_id) |

Note: "source" and "target" in column names refer to the direction of translation for this specific table (e.g., NL→RU), not a global privilege. The reverse pair (RU→NL) would be a separate table if needed.

### Decision: Per-User Word Lists via Junction Table

User word associations are stored in a junction table (`user_words`) that links `user_id` to word IDs in a specific language table.

**Table schema:**

| Column | Type | Constraints |
|---|---|---|
| `id` | SERIAL | PRIMARY KEY |
| `user_id` | VARCHAR | NOT NULL |
| `word_id` | INTEGER | FOREIGN KEY → language table |
| `language` | VARCHAR | NOT NULL (e.g., 'nl', 'ru') |
| `added_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() |
| | | UNIQUE(user_id, word_id, language) |

**Rationale:** (1) Simple, flat structure — no user registration needed. (2) `user_id` is a plain string, provided by the caller. (3) `language` column identifies which language table the `word_id` refers to. (4) `added_at` enables future features (chronological ordering, recent words).

### Decision: Abstract Backend Interface

Database operations are defined behind an abstract base class (`AbstractBackend`). The initial implementation (`NeonBackend`) targets Neon PostgreSQL via `asyncpg`.

**Rationale:** (1) 200ms latency threshold is a hard constraint — if Neon fails the threshold, swapping to another backend must be feasible without rewriting business logic. (2) Testing can use a mock or in-memory backend.

```python
class AbstractBackend(ABC):
    @abstractmethod
    async def add_word(self, table: str, normalized_form: str, word_type: str) -> int | None:
        """Insert word if not exists, return row id. Return None if already exists."""
        ...
    @abstractmethod
    async def get_word(self, table: str, normalized_form: str) -> dict | None:
        """Return row dict {id, normalized_form, word_type} or None."""
        ...
    @abstractmethod
    async def add_translation_link(self, table: str, source_id: int, target_id: int) -> None: ...
    @abstractmethod
    async def get_user_words(self, user_id: str, language: str, **filters) -> list[dict]: ...
    @abstractmethod
    async def add_user_word(self, user_id: str, word_id: int, language: str) -> None: ...
    @abstractmethod
    async def create_tables(self, languages: list[str], pairs: list[tuple[str, str]]) -> None: ...
```

**Note:** The backend interface operates on primitives (`str`, `int`, `dict`), not `Word` objects. The `DatabaseService` layer handles conversion between `Word` model instances and backend primitives. This keeps the backend abstraction database-focused and model-agnostic.

### Decision: Neon PostgreSQL as First Backend

**Rationale:** (1) Serverless PostgreSQL — no infrastructure management. (2) Standard SQL — familiar, well-tooled. (3) `asyncpg` provides native async Python driver with excellent performance. (4) Free tier sufficient for development and initial usage.

**Connection:** Via `DATABASE_URL` environment variable (standard PostgreSQL connection string).

### Decision: Direct Dependency on `translate_word`

The `database` module directly imports and calls `translate_word.WordTranslator` for automatic translation of new words.

**Rationale:** (1) Simpler than callback/hook patterns — no injection needed. (2) Both modules are internal to `nl_processing` — tight coupling is acceptable. (3) Translation is an integral part of the word-addition flow, not an optional extension.

**Async pattern:** Translation runs as a fire-and-forget `asyncio.Task`. The `add_words()` method receives `list[Word]` (with `language` set to the source language), creates the task, and returns immediately. When translation completes, `translate_word` returns `list[Word]` (with `language` set to the target language). The callback stores the translated `Word` objects in the target language table and creates translation links. Failures are logged, not raised.

### Decision: Fire-and-Forget Async Translation

When `add_words()` adds new words, translation is triggered as a background `asyncio.Task`. The method returns immediately with feedback about which words were new/existing.

**Implications:**
- `get_words()` may return fewer pairs than expected if translations are still pending — untranslated words are excluded with a warning log
- Background task errors are logged at WARNING level, never raised to the caller
- No retry mechanism in v1 — if translation fails, the word remains untranslated until the next manual trigger

### Decision: Local Caching Layer

A caching wrapper (`CachedDatabaseService`) wraps `DatabaseService` and maintains an in-memory cache of recently-accessed data. The remote database remains the source of truth.

**Cache strategy:**
- Cache populated on reads (`get_words`) and writes (`add_words`)
- Cache invalidation: LRU-based with configurable max size
- Cache is per-instance (per-user), not shared across instances
- Cache is not persistent — lost on process restart

**Rationale:** (1) Reduces read latency for repeated access patterns. (2) Reduces load on Neon for common queries. (3) Simple in-memory dict — no external caching infrastructure.

### Decision: Structured Logging with Sentry Path

Module uses Python's `logging` module with a structured formatter. Console handler as the initial backend. Logger names are namespaced (`nl_processing.database.*`).

**Sentry integration path:** Add `sentry_sdk` with `LoggingIntegration` — captures WARNING+ logs automatically. No code changes in the module needed.

### Decision: Environment Variable Configuration — Fail Fast

Module requires `DATABASE_URL` environment variable. At instantiation time, if the variable is not set, the module raises `ConfigurationError` with a human-readable message including setup instructions.

**Rationale:** Consistent with the project convention that `OPENAI_API_KEY` is required for LLM modules. Database modules require `DATABASE_URL`. No default values, no fallback behavior.

### Decision: Async-First Public API

All public methods are `async def`. The module is designed for use in async Python applications.

**Rationale:** (1) Database I/O is inherently async — blocking would waste resources. (2) `asyncpg` is natively async. (3) Fire-and-forget translation requires an event loop. (4) Consistent with modern Python async patterns.

### Decision: Unified `Word` Model from `core`

The `database` module uses the `Word` model from `nl_processing.core.models` as the canonical data type for all word operations. Both `add_words()` and `get_words()` work with `Word` instances. This is the same model used by `extract_words_from_text` (output) and `translate_word` (input/output), ensuring zero-conversion data flow across the pipeline.

**Rationale:** (1) Single model for the entire pipeline — no mapping or conversion between modules. (2) All language tables share identical schema derived from `Word` fields. (3) New languages don't require schema changes — only a new table with the same schema. (4) `word_type` uses `PartOfSpeech` enum values, providing type safety while keeping DB storage as human-readable strings.

**Reconstruction on read:** When reading from a per-language table, `DatabaseService` constructs `Word` objects by:
1. Reading `normalized_form` and `word_type` from the DB row
2. Converting `word_type` string back to `PartOfSpeech` enum
3. Setting `language` programmatically based on the table being queried (e.g., `words_nl` → `Language.NL`)

---

## Module Internal Structure

```
nl_processing/database/
├── __init__.py                  # public exports: DatabaseService, CachedDatabaseService, create_tables
├── service.py                   # DatabaseService (public class), CachedDatabaseService
├── backend/
│   ├── __init__.py
│   ├── abstract.py              # AbstractBackend (ABC)
│   └── neon.py                  # NeonBackend (asyncpg implementation)
├── models.py                    # AddWordsResult, WordPair (module-internal models, NOT Word — that's in core)
├── exceptions.py                # ConfigurationError, DatabaseError
├── logging.py                   # Structured logging setup
├── testing.py                   # Test utilities: drop_all_tables, reset_database, count helpers (NOT production code)
└── docs/
    ├── product-brief-database-2026-03-02.md
    ├── prd_database.md
    └── architecture_database.md  # THIS DOCUMENT
```

---

## Test Strategy

### Unit Tests

Mock the abstract backend. Test `DatabaseService` logic: deduplication, user-word association, feedback generation, async translation task creation, get_words filtering/exclusion of untranslated words. No real database connection.

### Integration Tests

Real `asyncpg` connection to a Neon database (dev environment). Test: table creation, word addition with deduplication, translation link creation, user word list operations, latency benchmarks (200ms threshold).

### E2E Tests — Full Real-World Flow

E2e tests exercise the complete module against a real Neon database with real words, real translation via `translate_word`, and real user operations. These tests are the primary quality gate for the `database` module.

**E2E Test Scenarios:**

1. **Table lifecycle:** `create_tables()` creates all required tables (language tables, link tables, user_words). Verify tables exist and have correct schema. Then `drop_all_tables()` removes them cleanly.
2. **Word addition flow:** Add a batch of real Dutch words → verify they appear in `words_nl` → verify feedback correctly identifies new vs. existing → add same words again → verify all reported as existing, no duplicates in table.
3. **Async translation flow:** Add new Dutch words → verify `translate_word` is triggered → wait for translation to complete → verify translations appear in `words_ru` → verify translation links created in `translations_nl_ru`.
4. **User word list:** Add words as user "test_user_1" → verify user-word associations created → add words as user "test_user_2" (some overlapping) → verify each user sees only their words → verify shared corpus contains all words from both users.
5. **Get words with filtering:** Add words of various types (nouns, verbs, adjectives) → `get_words(word_type="noun")` returns only nouns → `get_words(limit=3, random=True)` returns exactly 3 → `get_words()` returns all with translations.
6. **Untranslated word exclusion:** Add new words → immediately call `get_words()` before translation completes → verify untranslated words are excluded → verify warning is logged → wait for translation → call `get_words()` again → verify all words now returned with translations.
7. **Latency benchmark:** Measure add/check operation latency across 50 word operations → assert p95 ≤ 200ms.

### Backdoor / Test Utility Functions

E2e tests require the ability to reset the database to a clean state before and after test runs. The module provides **test utility functions** (not part of the public API) for this purpose:

```python
# nl_processing/database/testing.py — test utilities only, not for production use

async def drop_all_tables(languages: list[str], pairs: list[tuple[str, str]]) -> None:
    """Drop all word tables, translation link tables, and user_words table. Irreversible."""

async def reset_database(languages: list[str], pairs: list[tuple[str, str]]) -> None:
    """Drop all tables and recreate them empty. Equivalent to drop_all + create_tables."""

async def count_words(table: str) -> int:
    """Return the number of rows in a word table. For test assertions."""

async def count_user_words(user_id: str, language: str) -> int:
    """Return the number of words associated with a user. For test assertions."""

async def count_translation_links(table: str) -> int:
    """Return the number of translation links. For test assertions."""
```

**Design rationale:** These functions live in a separate `testing.py` file, clearly separated from production code. They are imported only by test files, never by production code. They use the same `DATABASE_URL` environment variable and backend abstraction as the main module.

### Doppler Environment Strategy for Testing

The `DATABASE_URL` in each Doppler environment points to a **different Neon database**:

| Doppler Environment | Neon Database | Purpose | Stability |
|---|---|---|---|
| `dev` | `nl_processing_dev` | Development and **all automated tests** (unit, integration, e2e) | Ephemeral — wiped by tests, recreated freely |
| `stg` | `nl_processing_stg` | Pre-production validation, manual testing | Stable — not wiped by automated tests |
| `prd` | `nl_processing_prd` | Production data | Stable — never touched by tests |

**Key rules:**
- All `doppler run -- make check` and CI pipeline runs use the `dev` environment → tests freely create/drop/reset tables in the dev database
- E2e tests **always** start with `reset_database()` in setup and `drop_all_tables()` in teardown — dev database is always left clean
- `stg` and `prd` databases are **never** touched by automated tests — they accumulate real data
- The `create_tables()` convenience function is safe to call in any environment (it uses `IF NOT EXISTS`) — but `drop_all_tables()` and `reset_database()` should only ever be called against the dev database

### Test File Structure

```
tests/
├── unit/database/
│   ├── __init__.py
│   ├── test_service.py              # DatabaseService logic with mocked backend
│   ├── test_deduplication.py        # Word deduplication logic
│   └── test_feedback.py             # AddWordsResult generation
├── integration/database/
│   ├── __init__.py
│   ├── test_neon_backend.py         # NeonBackend CRUD operations against real Neon
│   ├── test_table_creation.py       # create_tables() and drop_all_tables()
│   └── test_latency.py             # 200ms latency benchmark
└── e2e/database/
    ├── __init__.py
    ├── conftest.py                  # reset_database() in setup, drop_all_tables() in teardown
    ├── test_word_addition_flow.py   # Scenarios 2, 3 (add words, verify translation)
    ├── test_user_word_lists.py      # Scenarios 4, 5 (multi-user, filtering)
    └── test_untranslated_words.py   # Scenario 6 (exclusion, logging)
```
