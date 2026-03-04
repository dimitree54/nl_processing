---
Task ID: `T5`
Title: `Implement DatabaseService — replace save_translation placeholder`
Sprint: `2026-03-04_database-and-sampling`
Module: `database`
Depends on: `T4`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

`DatabaseService` is the primary public class of the database module. It provides `add_words()`, `get_words()`, and `create_tables()` methods. This task also removes the legacy `save_translation` placeholder and its vulture whitelist entry.

## Context (contract mapping)

- Requirements: `nl_processing/database/docs/prd_database.md` — FR1-FR22 (all core functionality)
- Architecture: `nl_processing/database/docs/architecture_database.md` — DatabaseService in service.py, fire-and-forget translation, Word model reconstruction

## Preconditions

- T4 complete (NeonBackend available)
- T2 complete (exceptions, models available)
- `nl_processing/translate_word/service.py` exists with `WordTranslator` class

## Non-goals

- No CachedDatabaseService (that's T7)
- No ExerciseProgressStore (that's T6)
- No unit tests (that's T9)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**

- `nl_processing/database/service.py` — rewrite (replace `save_translation`)
- `vulture_whitelist.py` — remove `save_translation` entry

**FORBIDDEN — this task must NEVER touch:**

- `nl_processing/database/__init__.py` (must stay empty)
- `nl_processing/translate_word/` (only import from it)
- Any other module's code or tests

**Test scope:**

- No new tests in this task
- `make check` must pass with existing 26 tests (minus references to old `save_translation` if any — there are none outside vulture_whitelist)

## Touched surface (expected files / modules)

- `nl_processing/database/service.py` (rewrite)
- `vulture_whitelist.py` (remove `save_translation` entry)

## Dependencies and sequencing notes

- Depends on T4 (NeonBackend)
- T6 (ExerciseProgressStore), T7 (CachedDatabaseService), T8 (testing.py), T9 (unit tests) all depend on this

## Third-party / library research (mandatory for any external dependency)

- **Library**: asyncio (stdlib) — for `asyncio.create_task()` used in fire-and-forget translation
  - **Docs**: https://docs.python.org/3.12/library/asyncio-task.html#asyncio.create_task
  - `create_task(coro)` schedules coroutine and returns a Task. The task runs in background.
- **Internal dependency**: `nl_processing.translate_word.service.WordTranslator`
  - `await translator.translate(words: list[Word]) -> list[Word]`
  - Architecture explicitly approves this direct dependency

## Implementation steps (developer-facing)

1. **Remove legacy code:**
   - Delete the entire contents of `nl_processing/database/service.py` (the `save_translation` function)
   - Edit `vulture_whitelist.py`: remove the line `from nl_processing.database.service import save_translation` and its entry from `__all__`

2. **Implement `DatabaseService` in `nl_processing/database/service.py`:**

   ```python
   class DatabaseService:
       def __init__(self, *, user_id: str,
                    source_language: Language = Language.NL,
                    target_language: Language = Language.RU) -> None:
   ```

   - Constructor reads `os.environ["DATABASE_URL"]` — wraps `KeyError` in `ConfigurationError` with setup instructions
   - Creates `NeonBackend(database_url)` internally
   - Creates `WordTranslator(source_language=..., target_language=...)` for async translation
   - Stores `user_id`, languages, backend, translator

3. **Implement `add_words(self, words: list[Word]) -> AddWordsResult`:**
   - For each word: call `backend.add_word(table, word.normalized_form, word.word_type.value)`
   - Track which words are new (returned id) vs existing (returned None)
   - Call `backend.add_user_word(user_id, word_id, language)` for all words (new and existing) — need to get word_id for existing words via `backend.get_word()`
   - For new words: create fire-and-forget `asyncio.create_task()` for translation
   - The translation callback: when translator returns `list[Word]`, store each translated word in target language table, create translation links
   - Return `AddWordsResult(new_words=..., existing_words=...)`

4. **Implement the translation callback** (private async method):
   - `async def _translate_and_store(self, new_words: list[Word]) -> None`
   - Call `self._translator.translate(new_words)` → `list[Word]` with target language
   - For each translated word: `backend.add_word(target_table, ...)`, then `backend.add_translation_link(...)`
   - Wrap in try/except — log warnings on failure, never raise (fire-and-forget per spec)

5. **Implement `get_words(self, *, word_type=None, limit=None, random=False) -> list[WordPair]`:**
   - Call `backend.get_user_words(user_id, source_lang, word_type, limit, random)`
   - Backend returns joined rows with source + target word data
   - Reconstruct `Word` objects (set `language` programmatically per architecture)
   - Exclude untranslated words (log warning for each excluded word)
   - Return `list[WordPair]`

6. **Implement `create_tables(cls)` class method:**
   - `@classmethod async def create_tables(cls) -> None`
   - Reads `DATABASE_URL` from env, creates temporary NeonBackend
   - Calls `backend.create_tables(languages=["nl", "ru"], pairs=[("nl", "ru")])`

7. **200-line awareness**: `DatabaseService` has constructor + 3 public methods + 1 private helper. Should fit within 200 lines. If tight, extract the translation callback into a separate private module.

8. Run `make check` — verify all linters pass, existing tests still pass (save_translation is no longer needed).

## Production safety constraints (mandatory)

- **Database operations**: No connections made unless the code is executed. Service only stores the URL.
- **Resource isolation**: `DATABASE_URL` from Doppler dev environment.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Uses `WordTranslator` from `translate_word` — no reimplementation.
- **Correct libraries only**: All imports from project packages or stdlib.
- **Correct file locations**: `service.py` per architecture.
- **No regressions**: `save_translation` is replaced (not left alongside new code). Vulture whitelist cleaned.

## Error handling + correctness rules (mandatory)

- `ConfigurationError` raised if `DATABASE_URL` is missing — with human-readable setup instructions.
- `DatabaseError` propagated from backend failures.
- Translation failures logged at WARNING, never raised (fire-and-forget).
- Untranslated words excluded from `get_words` with WARNING log.

## Zero legacy tolerance rule (mandatory)

- `save_translation` function MUST be deleted from `service.py`.
- Its vulture whitelist entry MUST be removed from `vulture_whitelist.py`.
- No backward compatibility — this is a complete replacement.

## Acceptance criteria (testable)

1. `nl_processing/database/service.py` contains `DatabaseService` class with `add_words`, `get_words`, `create_tables` methods.
2. `save_translation` function is gone from `service.py`.
3. `vulture_whitelist.py` no longer references `save_translation`.
4. `DatabaseService.__init__` raises `ConfigurationError` when `DATABASE_URL` is unset.
5. `create_tables` is a `@classmethod`.
6. All public methods are `async def`.
7. File is under 200 lines.
8. `make check` passes (all linters + existing tests; tests don't call save_translation).

## Verification / quality gates

- [ ] DatabaseService implemented with correct interface
- [ ] save_translation removed, vulture whitelist cleaned
- [ ] ConfigurationError raised for missing DATABASE_URL
- [ ] Fire-and-forget translation uses asyncio.create_task
- [ ] File under 200 lines
- [ ] `make check` passes

## Edge cases

- `add_words([])` — empty list should return `AddWordsResult(new_words=[], existing_words=[])` without creating tasks.
- `add_words` with mixed languages in the word list — architecture says `add_words` adds words to "the appropriate language table (determined by `Word.language`)". All words should be added to their respective language tables but only source-language words trigger translation.
- `get_words` when no translations exist — returns empty list with warning log.
- `DATABASE_URL` missing at `__init__` time — `ConfigurationError` with clear message.

## Notes / risks

- **Risk**: Fire-and-forget tasks may not complete before test assertions.
  - **Mitigation**: Unit tests (T9) mock the translator. E2e tests (T11) wait explicitly.
- **Risk**: `os.environ["DATABASE_URL"]` in constructor may fail in unit test environments.
  - **Mitigation**: Unit tests (T9) will use `monkeypatch.setenv`.
