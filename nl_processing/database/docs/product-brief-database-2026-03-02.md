---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - docs/planning-artifacts/product-brief.md
  - docs/planning-artifacts/prd.md
  - docs/planning-artifacts/architecture.md
  - nl_processing/extract_text_from_image/docs/planning-artifacts/product-brief-extract_text_from_image-2026-03-01.md
  - nl_processing/extract_words_from_text/docs/product-brief-extract_words_from_text-2026-03-01.md
  - nl_processing/translate_text/docs/product-brief-translate_text-2026-03-01.md
  - nl_processing/translate_word/docs/product-brief-translate_word-2026-03-01.md
date: 2026-03-02
author: Dima
parentBrief: docs/planning-artifacts/product-brief.md
---

# Product Brief: database

> For shared project context (technology stack, target users, design principles), see the [shared product brief](../../../docs/planning-artifacts/product-brief.md).

## Executive Summary

`database` is a highly independent persistence module for the `nl_processing` project. It provides a class-based async interface for storing, linking, and retrieving words across multiple languages using a shared relational database. The module manages per-language word tables, cross-language translation link tables, and per-user word lists — all behind a minimal public API where the developer instantiates a client with a `user_id` and immediately starts working.

The module has a direct dependency on `translate_word` — when new words are added, translation is triggered asynchronously. The user receives immediate feedback on which words were new vs. already known, without waiting for translations to complete.

The module follows the project's zero-config philosophy: environment variables for database connection are the only required setup (with a clear error and setup instructions if missing), and all other parameters use sensible defaults. A convenience function creates all required database tables in a single call.

Initial implementation targets Neon (serverless PostgreSQL) as the database backend, with abstract interfaces to support future backend swaps.

### What Makes This Module Special

- **Symmetric language architecture:** No language is treated as "source" or "target" — each language has its own word table, and translation links are stored separately per language pair. This makes the system naturally extensible to any language combination.
- **Fire-and-forget translation:** When new words are added, translation is triggered asynchronously via `translate_word`. The user gets immediate feedback on which words were new vs. already known, without waiting for translations to complete.
- **User-scoped word lists:** Each user has a personal list of "known words" referencing the shared global word tables. Adding words is a personal action; the word corpus is shared.
- **Local caching layer:** A cache wrapper keeps recently-accessed data local for fast reads, with the remote database as the source of truth.
- **Backend abstraction:** Core database operations are defined behind abstract interfaces, allowing future backend swaps. The initial implementation targets Neon PostgreSQL with a hard 200ms latency threshold — if exceeded during development, the backend choice is reconsidered.
- **Structured logging:** Logging is abstracted for easy future Sentry integration, with console output as the initial backend.

---

## Core Vision

### Problem Statement

The `nl_processing` pipeline modules (`extract_words_from_text`, `translate_word`, etc.) process words and translations but have no persistence layer. Results are ephemeral — every pipeline run starts from scratch. There is no shared word corpus that grows over time, no way to track which words a specific user has encountered, and no mechanism to avoid redundant translation of already-known words.

### Problem Impact

- Every pipeline execution re-processes words that were already extracted and translated in previous runs
- No accumulation of a growing multilingual word corpus across users
- No per-user tracking of learned/encountered vocabulary
- No way to know which words still need translation vs. which are already translated
- Translation API costs scale linearly with repeated runs instead of only paying for genuinely new words

### Why Existing Solutions Fall Short

- **In-memory storage (current `service.py`):** Data is lost between runs. No persistence, no multi-user support, no structure.
- **Generic ORMs / database libraries:** Require significant boilerplate to set up the specific table structure, relationships, caching, and async patterns needed. The developer would need to understand the data model deeply.
- **External dictionary/vocabulary services:** Don't integrate with the project's specific word models and translation pipeline.

### Proposed Solution

An async Python module that:
- Provides a `DatabaseService` class instantiated with `user_id` (string) and minimal optional configuration
- Manages per-language word tables (unified word model: `normalized_form`, `language`, `word_type`), per-language-pair translation link tables, and per-user word lists
- Exposes two primary methods: `add_words(words)` — adds words, triggers async translation via `translate_word`, returns immediate feedback; `get_words(...)` — retrieves user's word-translation pairs with optional filtering (by word_type, limit, random sampling)
- Provides a one-time `create_tables()` convenience function for initial setup
- Uses abstract backend interface with Neon PostgreSQL as the first implementation
- Includes a local caching layer for performance optimization
- Enforces ≤200ms latency per add/check operation as a hard development-time constraint
- Requires database connection via environment variables — fails fast with clear setup instructions if missing
- Uses structured logging abstraction (console now, Sentry-ready)
- Depends directly on `translate_word` for automatic translation of newly added words

---

## Success Metrics

### Acceptance Criteria

1. **Add/check latency:** ≤200ms per single word add/existence-check operation against Neon PostgreSQL (wall clock time). If exceeded during development — stop and report.
2. **Correctness:** Words added once are never duplicated. Translation links are created correctly. User word lists reference the shared corpus accurately.
3. **Async translation:** Adding words returns feedback immediately; translation happens asynchronously without blocking the caller.
4. **Get words:** Returns word-translation pairs for the user. Words not yet translated are excluded with a warning logged.

### Readiness Criteria

- All database operations complete within 200ms latency threshold
- Convenience `create_tables()` function creates all required tables
- Module fails fast with clear instructions when environment variables are missing
- Integration tests pass against a real Neon database

---

## Scope

This module has no MVP/phased delivery — it is a single, indivisible unit.

### Core Features

1. **`DatabaseService` class** with `user_id` constructor, minimal optional parameters, sensible defaults
2. **Per-language word tables** — separate table per language (e.g., `words_nl`, `words_ru`), unified word model (`normalized_form`, `word_type`)
3. **Translation link tables** — separate table per language pair (e.g., `translations_nl_ru`), references both language tables
4. **Per-user word lists** — user's known words referencing the shared word tables
5. **`add_words(words)`** — adds words to shared table (deduplication), triggers async translation via `translate_word`, records user-word associations, returns feedback (new vs. existing)
6. **`get_words(...)`** — retrieves user's word-translation pairs with optional filtering: `word_type`, `limit`, random sampling
7. **`create_tables()`** — one-time convenience function to create all required tables (empty)
8. **Backend abstraction** — abstract interfaces for database operations, first implementation: Neon PostgreSQL
9. **Local caching layer** — wrapper for fast reads of recently-accessed data
10. **Structured logging** — abstraction for console logging now, Sentry-ready later
11. **Async-first** — all public methods are async
12. **Environment variable configuration** — fail-fast with setup instructions if missing
13. **Test utilities** — `drop_all_tables()`, `reset_database()`, count helpers for e2e test setup/teardown (separate `testing.py`, not production code)

### Module-Specific Dependencies

- `asyncpg` — async PostgreSQL driver for Neon
- `translate_word` — direct dependency for automatic translation of new words

### Out of Scope

- User authentication or registration (user_id is a plain string)
- Database migrations or schema versioning
- Full-text search or fuzzy matching
- Bulk import/export functionality
- Admin interface or database management UI
- Languages other than Dutch and Russian (interface supports them, only NL/RU tables are created and tested)

### Future Vision

- Additional language tables and translation link tables as new languages are added to the project
- Database migration tooling if schema evolves
- More sophisticated caching strategies (TTL, LRU, distributed cache)
- Additional query methods (search, statistics, frequency analysis)
