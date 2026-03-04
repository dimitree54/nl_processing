---
Sprint ID: `2026-03-04_database`
Sprint Goal: `Implement the database persistence module with async PostgreSQL backend, fire-and-forget translation, per-user word lists, and full test coverage at all three levels.`
Sprint Type: `module`
Module: `database`
Status: `planning`
---

## Goal

Replace the legacy placeholder `save_translation` function with a production-quality `database` module that persists words in Neon PostgreSQL via `asyncpg`, manages per-language word tables, translation link tables, and per-user word lists behind an abstract backend interface. The module triggers async translation of new words via `translate_word`, returns immediate feedback, and enforces a hard 200ms latency ceiling. All three test levels (unit, integration, e2e) must pass, and `make check` must be 100% green after every task.

## Module Scope

### What this sprint implements
- Module: `database`
- Architecture spec: `nl_processing/database/docs/architecture_database.md`
- PRD: `nl_processing/database/docs/prd_database.md`
- Product brief: `nl_processing/database/docs/product-brief-database-2026-03-02.md`

### Boundary Rules (STRICTLY ENFORCED)

**ALLOWED -- this sprint may ONLY touch:**
- `nl_processing/database/` -- module source code (replace `service.py`, create new files per architecture)
- `nl_processing/database/backend/` -- backend sub-package
- `tests/unit/database/` -- unit tests
- `tests/integration/database/` -- integration tests
- `tests/e2e/database/` -- e2e tests
- `pyproject.toml` -- add `asyncpg` dependency only
- `vulture_whitelist.py` -- update stale `save_translation` reference
- `tests/integration/extract_text_from_image/test_extraction_accuracy.py` -- fix flaky test (T1 only)

**FORBIDDEN -- this sprint must NEVER touch:**
- `nl_processing/core/` -- core package
- `nl_processing/extract_text_from_image/` -- different module
- `nl_processing/extract_words_from_text/` -- different module
- `nl_processing/translate_text/` -- different module
- `nl_processing/translate_word/` -- different module (consumed as dependency, not modified)
- Tests of other modules (except the T1 flaky test fix)
- Any bot code
- `Makefile`, `ruff.toml`, `pytest.ini`, `.jscpd.json` -- project-level config

### Test Scope
- **Unit test directory**: `tests/unit/database/`
- **Unit test command**: `uv run pytest tests/unit/database/ -x -v`
- **Integration test directory**: `tests/integration/database/`
- **Integration test command**: `doppler run -- uv run pytest tests/integration/database/ -x -v`
- **E2e test directory**: `tests/e2e/database/`
- **E2e test command**: `doppler run -- uv run pytest tests/e2e/database/ -x -v`
- **Full quality gate**: `make check` (must pass after every task)
- **NEVER run**: tests from other modules individually (but `make check` runs everything)

## Interface Contract

### Public interface this sprint implements

```python
from nl_processing.database.service import DatabaseService, CachedDatabaseService
from nl_processing.database.exceptions import ConfigurationError, DatabaseError
from nl_processing.database.models import AddWordsResult, WordPair
from nl_processing.core.models import Word, Language, PartOfSpeech

# One-time setup
await DatabaseService.create_tables()

# Per-user usage
db = DatabaseService(user_id="alex")
result: AddWordsResult = await db.add_words(words: list[Word])
# result.new_words: list[Word], result.existing_words: list[Word]

pairs: list[WordPair] = await db.get_words(
    word_type=PartOfSpeech.NOUN,  # optional
    limit=10,                      # optional
    random=True,                   # optional
)
# pairs[0].source -> Word, pairs[0].target -> Word
```

### Backend interface (internal)

```python
from nl_processing.database.backend.abstract import AbstractBackend

class AbstractBackend(ABC):
    async def add_word(self, table, normalized_form, word_type) -> int | None: ...
    async def get_word(self, table, normalized_form) -> dict | None: ...
    async def add_translation_link(self, table, source_id, target_id) -> None: ...
    async def get_user_words(self, user_id, language, **filters) -> list[dict]: ...
    async def add_user_word(self, user_id, word_id, language) -> None: ...
    async def create_tables(self, languages, pairs) -> None: ...
```

## Scope

### In
- Fix pre-existing flaky test in `extract_text_from_image` (establish green baseline)
- Add `asyncpg` to `pyproject.toml` dependencies
- Module exceptions: `ConfigurationError`, `DatabaseError`
- Module models: `AddWordsResult`, `WordPair`
- Structured logging setup
- Abstract backend interface (`AbstractBackend` ABC)
- Neon backend implementation (`NeonBackend` via `asyncpg`)
- `DatabaseService` with `create_tables()`, `add_words()`, `get_words()`
- `CachedDatabaseService` caching wrapper
- Test utilities in `testing.py`
- Unit tests (mocked backend)
- Integration tests (real Neon DB)
- E2e tests (real DB + real translation)
- Vulture whitelist cleanup

### Out
- Languages other than NL/RU (interface supports them; only NL/RU tables created and tested)
- Database migrations or schema versioning
- Full-text search or fuzzy matching
- Admin interface
- User authentication

## Inputs (contracts)

- Requirements: `nl_processing/database/docs/prd_database.md` (FR1-FR27, NFR1-NFR16)
- Architecture: `nl_processing/database/docs/architecture_database.md`
- Product brief: `nl_processing/database/docs/product-brief-database-2026-03-02.md`
- Shared architecture: `docs/planning-artifacts/architecture.md`
- Shared PRD: `docs/planning-artifacts/prd.md`
- Core models: `nl_processing/core/models.py` (Word, Language, PartOfSpeech)
- translate_word interface: `nl_processing/translate_word/service.py` (WordTranslator)

## Change digest

- **Requirement deltas**: None. Implementing FR1-FR27 and NFR1-NFR16 from scratch.
- **Architecture deltas**: None. Following architecture document as-is.
- **Legacy removal**: The 2-line `save_translation` placeholder in `service.py` will be completely replaced.

## Task list (dependency-aware)

- **T1:** `TASK_01_fix_flaky_test.md` (depends: --) (parallel: no) -- Fix pre-existing flaky integration test to establish green `make check` baseline
- **T2:** `TASK_02_infrastructure.md` (depends: T1) (parallel: no) -- Add `asyncpg` to pyproject.toml, create Neon dev database, configure Doppler
- **T3:** `TASK_03_exceptions_models_logging.md` (depends: T2) (parallel: no) -- Create `exceptions.py`, `models.py`, `logging.py` foundation files
- **T4:** `TASK_04_abstract_backend.md` (depends: T3) (parallel: no) -- Create `backend/abstract.py` with `AbstractBackend` ABC
- **T5:** `TASK_05_neon_backend.md` (depends: T4) (parallel: no) -- Implement `NeonBackend` in `backend/neon.py` using `asyncpg`
- **T6:** `TASK_06_database_service.md` (depends: T5) (parallel: no) -- Implement `DatabaseService` in `service.py` with `create_tables()`, `add_words()`, `get_words()`
- **T7:** `TASK_07_cached_service.md` (depends: T6) (parallel: no) -- Implement `CachedDatabaseService` caching wrapper in `service.py`
- **T8:** `TASK_08_testing_utilities.md` (depends: T6) (parallel: no) -- Create `testing.py` with `drop_all_tables()`, `reset_database()`, count helpers
- **T9:** `TASK_09_unit_tests.md` (depends: T6) (parallel: no) -- Create unit tests with mocked backend
- **T10:** `TASK_10_integration_tests.md` (depends: T8) (parallel: yes, with T9) -- Create integration tests against real Neon
- **T11:** `TASK_11_e2e_tests.md` (depends: T9, T10) (parallel: no) -- Create e2e tests with real DB + real translation
- **T12:** `TASK_12_vulture_cleanup.md` (depends: T6) (parallel: yes, with T9/T10/T11) -- Update vulture whitelist, final `make check` verification

## Dependency graph (DAG)

- T1 -> T2
- T2 -> T3
- T3 -> T4
- T4 -> T5
- T5 -> T6
- T6 -> T7
- T6 -> T8
- T6 -> T9
- T6 -> T12
- T8 -> T10
- T9 -> T11
- T10 -> T11

## Execution plan

### Critical path
- T1 -> T2 -> T3 -> T4 -> T5 -> T6 -> T9 -> T11

### Parallel tracks (lanes)
- **Lane A (foundation)**: T1, T2, T3, T4, T5, T6
- **Lane B (after T6)**: T7 || T8 || T9 || T12
- **Lane C (after T8 + T9)**: T10
- **Lane D (after T9 + T10)**: T11

## Production safety

The current application version is **running in production on this same machine** (different directory).

- **Production database**: `nl_processing_prd` on Neon -- NEVER touched by this sprint. All development and testing uses the `dev` Doppler environment pointing to `nl_processing_dev` Neon database.
- **Shared resource isolation**: Doppler environment separation ensures `DATABASE_URL` points to dev database during development and testing. Production Doppler environment (`prd`) is not accessed.
- **Migration deliverable**: `N/A` -- this is a greenfield module; tables are created from scratch via `create_tables()` using `IF NOT EXISTS`. No existing production data to migrate.

## Definition of Done (DoD)

All items must be true:

- All 12 tasks completed and verified
- Unit tests pass: `uv run pytest tests/unit/database/ -x -v`
- Integration tests pass: `doppler run -- uv run pytest tests/integration/database/ -x -v`
- E2e tests pass: `doppler run -- uv run pytest tests/e2e/database/ -x -v`
- `make check` passes 100% green (all modules, all test levels)
- Module isolation: no files outside the ALLOWED list were touched
- Public interface matches architecture spec exactly
- Zero legacy tolerance: `save_translation` placeholder completely removed
- No errors are silenced (no swallowed exceptions)
- Requirements/architecture docs unchanged
- Production database untouched; all development against `nl_processing_dev` only
- All files <= 200 lines (pylint enforced)
- All database operations <= 200ms (integration test enforced)

## Risks + mitigations

- **Risk**: Neon PostgreSQL latency may exceed 200ms for some operations due to cold starts.
  - **Mitigation**: Use connection pooling via `asyncpg.create_pool()`. Run latency benchmarks in integration tests. If 200ms is consistently exceeded, halt and report per NFR2.
- **Risk**: Fire-and-forget async translation may leak exceptions.
  - **Mitigation**: Wrap translation callback in try/except, log WARNING on failure. Unit tests verify no exception propagation.
- **Risk**: LLM nondeterminism in e2e tests (translation quality may vary).
  - **Mitigation**: Use unambiguous test words (common nouns). Assert translation exists and is linked, not exact translation text.
- **Risk**: The flaky `test_english_only_raises_target_language_not_found` test may be difficult to stabilize.
  - **Mitigation**: Add retry logic or loosen the assertion to account for LLM nondeterminism. The test is in another module's test file, which is explicitly allowed for T1 only.
- **Risk**: `service.py` may exceed 200 lines with both `DatabaseService` and `CachedDatabaseService`.
  - **Mitigation**: `CachedDatabaseService` is a thin wrapper. If needed, split into separate file.

## Migration plan (if data model changes)

N/A -- greenfield module. Tables created from scratch via `create_tables()` with `IF NOT EXISTS`.

## Rollback / recovery notes

- Revert all files in the ALLOWED list to their previous state
- Remove test directories: `tests/unit/database/`, `tests/integration/database/`, `tests/e2e/database/`
- Remove `asyncpg` from `pyproject.toml`
- The dev Neon database tables can be dropped manually or will be cleaned by e2e test teardown

## Task validation status

- Per-task validation order: `T1` -> `T2` -> `T3` -> `T4` -> `T5` -> `T6` -> `T7` -> `T8` -> `T9` -> `T10` -> `T11` -> `T12`
- Validator: `self-validated`
- Outcome: `approved`

## Sources used

- Requirements: `nl_processing/database/docs/prd_database.md`
- Architecture: `nl_processing/database/docs/architecture_database.md`
- Product brief: `nl_processing/database/docs/product-brief-database-2026-03-02.md`
- Shared architecture: `docs/planning-artifacts/architecture.md`
- Shared PRD: `docs/planning-artifacts/prd.md`
- Code read: `nl_processing/database/service.py` (legacy placeholder), `nl_processing/database/__init__.py`, `nl_processing/core/models.py`, `nl_processing/core/exceptions.py`, `nl_processing/translate_word/service.py`, `pyproject.toml`, `Makefile`, `pytest.ini`, `vulture_whitelist.py`, `.jscpd.json`, `tests/conftest.py`, `tests/integration/extract_text_from_image/test_extraction_accuracy.py`
- Existing sprint reference: `docs/sprints/module-translate-word/`
- Library research: `asyncpg` v0.31.0 (latest stable, PyPI Nov 2025), docs at `https://magicstack.github.io/asyncpg/current/`

## Contract summary

### What (requirements)
- FR1-FR4: Table creation (per-language word tables, translation links, user_words)
- FR5-FR10: Word management (add_words with dedup, feedback, async translation)
- FR11-FR15: Word retrieval (get_words with WordPair, filtering, limit, random)
- FR16-FR18: Configuration (DATABASE_URL, fail-fast, language params)
- FR19-FR22: Structured logging (console, Sentry-ready, warning for failures)
- FR23-FR27: Testing utilities (drop, reset, count helpers)
- NFR1-NFR4: Performance (200ms ceiling, caching, batch ops)
- NFR5-NFR7: Async (all public async, fire-and-forget translation, logged failures)
- NFR8-NFR9: Reliability (DatabaseError, connection pooling)
- NFR10-NFR14: Testing (real Neon, reset/teardown, latency benchmark)
- NFR15-NFR16: Dependencies (asyncpg, translate_word)

### How (architecture)
- Symmetric per-language tables (`words_nl`, `words_ru`)
- Per-language-pair translation links (`translations_nl_ru`)
- Per-user word lists (`user_words` junction table)
- `AbstractBackend` ABC -> `NeonBackend` (asyncpg)
- `DatabaseService` orchestrates backend + translation
- `CachedDatabaseService` wraps DatabaseService with LRU cache
- `Word` model from `core.models` as canonical data type
- `DATABASE_URL` via `os.environ[]`, fail-fast `ConfigurationError`
- Fire-and-forget `asyncio.Task` for translation

## Impact inventory (implementation-facing)

- **Module**: `database` (`nl_processing/database/`)
- **Interfaces**: `DatabaseService.create_tables()`, `DatabaseService.add_words()`, `DatabaseService.get_words()`, `CachedDatabaseService`
- **Data model**: Uses `Word` from `core` (already defined). Creates `AddWordsResult`, `WordPair` locally.
- **Database schema**: `words_nl`, `words_ru`, `translations_nl_ru`, `user_words` tables in Neon PostgreSQL
- **External services**: Neon PostgreSQL (via `asyncpg`), OpenAI API (via `translate_word`)
- **Test directories**: `tests/unit/database/`, `tests/integration/database/`, `tests/e2e/database/`
