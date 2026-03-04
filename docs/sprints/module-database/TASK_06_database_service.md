---
Task ID: `T6`
Title: `Implement DatabaseService in service.py with create_tables, add_words, get_words`
Sprint: `2026-03-04_database`
Module: `database`
Depends on: `T5`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

The primary public class `DatabaseService` exists in `service.py`, replacing the legacy `save_translation` placeholder. It provides `create_tables()` (class method), `add_words()`, and `get_words()` -- orchestrating the `NeonBackend`, converting between `Word` models and backend primitives, and triggering fire-and-forget async translation via `translate_word`. This is the core deliverable of the module.

## Context (contract mapping)

- Requirements: `nl_processing/database/docs/prd_database.md` -- FR1 (create_tables), FR5-FR10 (add_words), FR11-FR15 (get_words), FR16-FR18 (configuration), FR21-FR22 (logging warnings)
- Architecture: `nl_processing/database/docs/architecture_database.md` -- "DatabaseService", "Fire-and-Forget Async Translation", "Unified Word Model from core", "Model-to-Database Mapping"
- PRD API surface: `nl_processing/database/docs/prd_database.md` -- "API Surface" section

## Preconditions

- T5 completed: `NeonBackend` exists and implements `AbstractBackend`.
- T3 completed: `exceptions.py`, `models.py`, `logging.py` exist.
- `translate_word.WordTranslator` is available (existing module, not modified).

## Non-goals

- `CachedDatabaseService` (T7)
- `testing.py` utilities (T8)
- Tests (T9-T11)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `nl_processing/database/service.py` -- replace entirely (remove legacy `save_translation`)

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/core/` -- core package
- `nl_processing/translate_word/` -- consumed as dependency, not modified
- `nl_processing/database/backend/` -- already created
- `nl_processing/database/exceptions.py`, `models.py`, `logging.py` -- already created
- Any test files
- Other modules

**Test scope:**
- No automated tests in this task. Formal testing in T9-T11.
- Manual verification via REPL.

## Touched surface (expected files / modules)

- `nl_processing/database/service.py` -- complete replacement

## Dependencies and sequencing notes

- Depends on T5 for `NeonBackend`.
- T7 (CachedDatabaseService), T8 (testing.py), T9 (unit tests), T12 (vulture) all depend on this.
- This task consumes `translate_word.WordTranslator` via import (direct dependency per architecture).

## Third-party / library research (mandatory for any external dependency)

- **Library**: `asyncio` (stdlib)
  - `asyncio.create_task(coro)` -- schedule a coroutine as a background task (fire-and-forget)
  - Docs: https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
  - **Gotcha**: The task must be referenced to prevent garbage collection. Store in a set and use `task.add_done_callback()` to remove.
- **Module**: `nl_processing.translate_word.service.WordTranslator`
  - `WordTranslator(source_language=Language.NL, target_language=Language.RU)`
  - `await translator.translate(words: list[Word]) -> list[Word]`
  - Returns `list[Word]` with `language` set to target language

## Implementation steps (developer-facing)

### 1. Delete the entire contents of `service.py`

Remove the legacy `save_translation` function completely.

### 2. Implement `DatabaseService` class

The class structure:

```python
import asyncio

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database.backend.neon import NeonBackend
from nl_processing.database.exceptions import DatabaseError
from nl_processing.database.logging import get_logger
from nl_processing.database.models import AddWordsResult, WordPair
from nl_processing.translate_word.service import WordTranslator

_logger = get_logger("service")

# Set to hold references to background translation tasks
_background_tasks: set[asyncio.Task] = set()  # type: ignore[type-arg]


class DatabaseService:
    """Async persistence service for words, translations, and user word lists.

    Usage:
        await DatabaseService.create_tables()
        db = DatabaseService(user_id="alex")
        result = await db.add_words(words)
        pairs = await db.get_words()
    """

    _LANGUAGES = [Language.NL.value, Language.RU.value]
    _PAIRS = [(Language.NL.value, Language.RU.value)]

    def __init__(
        self,
        user_id: str,
        *,
        source_language: Language = Language.NL,
        target_language: Language = Language.RU,
    ) -> None:
        self._user_id = user_id
        self._source_language = source_language
        self._target_language = target_language
        self._backend = NeonBackend()
        self._translator = WordTranslator(
            source_language=source_language,
            target_language=target_language,
        )
    ...
```

### 3. Implement `create_tables()` class method

```python
@classmethod
async def create_tables(cls) -> None:
    """Create all required database tables (IF NOT EXISTS).

    Safe to call multiple times -- uses IF NOT EXISTS semantics.
    """
    backend = NeonBackend()
    await backend.create_tables(cls._LANGUAGES, cls._PAIRS)
```

### 4. Implement `add_words()`

```python
async def add_words(self, words: list[Word]) -> AddWordsResult:
    """Add words to the corpus and trigger async translation.

    Returns feedback on which words were new vs. already known.
    Triggers background translation for new words only.
    """
    new_words: list[Word] = []
    existing_words: list[Word] = []
    src_table = f"words_{self._source_language.value}"

    for word in words:
        row_id = await self._backend.add_word(
            src_table, word.normalized_form, word.word_type.value
        )
        if row_id is not None:
            new_words.append(word)
        else:
            existing_words.append(word)

        # Get the word's DB id for user association
        db_word = await self._backend.get_word(src_table, word.normalized_form)
        if db_word is not None:
            await self._backend.add_user_word(
                self._user_id, db_word["id"], self._source_language.value
            )

    # Trigger async translation for new words (fire-and-forget)
    if new_words:
        task = asyncio.create_task(self._translate_and_store(new_words))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    return AddWordsResult(new_words=new_words, existing_words=existing_words)
```

### 5. Implement `_translate_and_store()` (private async callback)

```python
async def _translate_and_store(self, words: list[Word]) -> None:
    """Background task: translate words and store results.

    Failures are logged as warnings, never raised to caller.
    """
    try:
        translated = await self._translator.translate(words)
        tgt_table = f"words_{self._target_language.value}"
        link_table = (
            f"translations_{self._source_language.value}"
            f"_{self._target_language.value}"
        )
        src_table = f"words_{self._source_language.value}"

        for source_word, target_word in zip(words, translated):
            # Store translated word
            await self._backend.add_word(
                tgt_table, target_word.normalized_form,
                target_word.word_type.value,
            )
            # Get IDs for link
            src_row = await self._backend.get_word(
                src_table, source_word.normalized_form
            )
            tgt_row = await self._backend.get_word(
                tgt_table, target_word.normalized_form
            )
            if src_row and tgt_row:
                await self._backend.add_translation_link(
                    link_table, src_row["id"], tgt_row["id"]
                )
    except Exception:
        _logger.warning(
            "Background translation failed for %d words",
            len(words),
            exc_info=True,
        )
```

### 6. Implement `get_words()`

```python
async def get_words(
    self,
    *,
    word_type: PartOfSpeech | None = None,
    limit: int | None = None,
    random: bool = False,
) -> list[WordPair]:
    """Get user's word-translation pairs.

    Words without completed translations are excluded with a warning.
    """
    filters: dict[str, object] = {}
    if word_type is not None:
        filters["word_type"] = word_type.value
    if limit is not None:
        filters["limit"] = limit
    if random:
        filters["random"] = True

    user_words = await self._backend.get_user_words(
        self._user_id, self._source_language.value, **filters
    )

    pairs: list[WordPair] = []
    link_table = (
        f"translations_{self._source_language.value}"
        f"_{self._target_language.value}"
    )
    tgt_table = f"words_{self._target_language.value}"
    untranslated_count = 0

    for row in user_words:
        # Find translation link
        # Query the translation link table for this word
        source_word = Word(
            normalized_form=row["normalized_form"],
            word_type=PartOfSpeech(row["word_type"]),
            language=self._source_language,
        )
        # ... look up translation via backend
        # If no translation exists, log warning and skip
        # If translation exists, construct WordPair

    if untranslated_count > 0:
        _logger.warning(
            "%d words excluded from results (translation pending)",
            untranslated_count,
        )

    return pairs
```

**Note**: The full `get_words` implementation requires querying the translation link table to find matching translations. The exact SQL join pattern should be implemented as a backend helper or via multiple backend calls. The developer should choose the approach that keeps the file under 200 lines.

**Key implementation detail for `get_words`**: The backend's `get_user_words` returns source word rows. For each source word, the service must:
1. Query the translation link table for `source_word_id = row["id"]`
2. If a link exists, fetch the target word from the target language table
3. Reconstruct both source and target `Word` objects with proper `language` field
4. If no link exists, increment `untranslated_count` and skip

This may require adding a helper method to the backend (e.g., `get_translation` or doing a JOIN in `get_user_words`). The developer should choose the cleanest approach that fits within 200 lines. If a backend helper is needed, it can be added to `NeonBackend` (extending the backend interface is acceptable within this sprint).

### 7. Verify file is under 200 lines

If `service.py` approaches 200 lines with just `DatabaseService`:
- Move the `_background_tasks` set and `_translate_and_store` to module level
- Keep docstrings concise
- `CachedDatabaseService` will be added in T7 -- if the file risks exceeding 200 lines, T7 can create a separate file

### 8. Run `make check`

## Production safety constraints (mandatory)

- **Database operations**: No DB operations run during this task (code only). The service reads `DATABASE_URL` via `NeonBackend` constructor.
- **Resource isolation**: Doppler `dev` environment only.

## Anti-disaster constraints (mandatory)

- `translate_word.WordTranslator` is imported and called -- it's an existing, tested module.
- `Word` model from `core.models` is used for all public interfaces (zero-conversion pipeline).
- Uses `os.environ[]` convention (via NeonBackend) -- never `os.getenv()`.
- Fire-and-forget tasks are properly referenced in `_background_tasks` set to prevent GC.

## Error handling + correctness rules (mandatory)

- `_translate_and_store` catches ALL exceptions and logs WARNING -- fire-and-forget must never leak (FR21).
- `get_words` logs WARNING for untranslated words (FR22).
- `DatabaseError` propagates from `NeonBackend` for DB failures in `add_words` and `get_words` (not silenced).
- No empty catch blocks in public methods.

## Zero legacy tolerance rule (mandatory)

- Legacy `save_translation` function is **completely deleted** from `service.py`.
- No backward-compatible wrapper or import alias.

## Acceptance criteria (testable)

1. `service.py` contains `DatabaseService` class (legacy `save_translation` deleted)
2. `DatabaseService.__init__` accepts `user_id`, `source_language`, `target_language`
3. `DatabaseService.create_tables()` is an async class method
4. `add_words(words: list[Word])` returns `AddWordsResult` with `new_words` and `existing_words`
5. `add_words` triggers background translation for new words via `asyncio.create_task`
6. `_translate_and_store` logs WARNING on failure, never raises
7. `get_words()` returns `list[WordPair]` with source and target `Word` objects
8. `get_words()` excludes untranslated words with WARNING logged
9. `get_words()` accepts optional `word_type`, `limit`, `random` parameters
10. All public methods are `async def`
11. File under 200 lines
12. `make check` passes 100% green

## Verification / quality gates

- [ ] Ruff format and check pass
- [ ] Pylint 200-line limit passes
- [ ] Legacy `save_translation` deleted
- [ ] Import works: `from nl_processing.database.service import DatabaseService`
- [ ] `make check` passes 100% green
- [ ] No errors silenced in public methods

## Edge cases

- `add_words([])` -- empty list: returns `AddWordsResult(new_words=[], existing_words=[])`, no translation triggered.
- All words already exist: `new_words=[]`, no translation triggered.
- `get_words()` with no words in DB: returns empty list.
- `get_words()` when all words are untranslated: returns empty list with WARNING logged.
- Translation fails: WARNING logged, words remain in source table but no link created. Next `add_words` call won't re-trigger translation (words already exist).
- Concurrent `add_words` calls: `ON CONFLICT DO NOTHING` in backend handles dedup safely.

## Notes / risks

- **Risk**: `service.py` may be tight on the 200-line limit with `DatabaseService` alone. Keep methods concise. `CachedDatabaseService` (T7) may need its own file if `service.py` is near the limit.
- **Decision made autonomously**: Using a module-level `_background_tasks` set (not instance-level) for fire-and-forget task references. This is simpler and matches `asyncio.create_task` best practices.
- **Decision made autonomously**: `create_tables()` is a `@classmethod` that creates its own `NeonBackend` instance. This avoids requiring a `DatabaseService` instance just to create tables.
