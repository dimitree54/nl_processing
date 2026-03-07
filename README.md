# nl_processing

[![PyPI](https://img.shields.io/pypi/v/nl_processing)](https://pypi.org/project/nl_processing/)

Dutch language processing toolkit powered by LangChain + OpenAI.

## Installation

```bash
pip install nl_processing
```

## Modules

| Module | Class | Description | Docs |
|--------|-------|-------------|------|
| `extract_text_from_image` | `ImageTextExtractor` | Extract Dutch text from images via Vision API | [docs](nl_processing/extract_text_from_image/docs/) |
| `extract_words_from_text` | `WordExtractor` | Extract and normalize words from markdown text | [docs](nl_processing/extract_words_from_text/docs/) |
| `translate_text` | `TextTranslator` | Translate text (NL → RU) with markdown preservation | [docs](nl_processing/translate_text/docs/) |
| `translate_word` | `WordTranslator` | Batch-translate words (NL → RU) | [docs](nl_processing/translate_word/docs/) |
| `database` | `DatabaseService` | Remote source-of-truth persistence for words, translations, and exercise scores | [docs](nl_processing/database/docs/) |
| `sampling` | `WordSampler` | Weighted word sampling with adversarial distractors | [docs](nl_processing/sampling/docs/) |
| `database_cache` | `DatabaseCacheService` | Local-first cache for vocabulary practice (planned) | [docs](nl_processing/database_cache/docs/) |

Each module's `docs/` folder contains a product brief, PRD, and architecture doc.

## Recommended: `database_cache` for Interactive Practice

> **Status:** `database_cache` is currently in the design/documentation phase. The implementation is planned.

`database_cache` is a local-first cache module that accelerates the vocabulary practice loop. It sits in front of the remote `database` module and keeps a durable local snapshot of translated words and exercise statistics using SQLite. All reads are served entirely from local storage (sub-200ms).

### Why Use It

- **Interactive practice sessions** — word retrieval and score-aware sampling without network latency.
- **Offline score recording** — exercise outcomes are written locally first and synced later.
- **Stale-while-revalidate** — a stale cache is served immediately while a background refresh happens.
- **Safe sync** — pending local writes use idempotent event IDs, so retries never double-apply scores.
- **Exercise-aware** — initialized with specific `exercise_types`, mirrors the remote per-exercise-type tables.

### How It Works

1. Initialized with `user_id`, language pair, `exercise_types`, and `cache_ttl`.
2. On `init()`: opens/creates local SQLite, returns `CacheStatus`, starts background refresh if stale.
3. `get_words()` and `get_word_pairs_with_scores()` — read from local cache only.
4. `record_exercise_result()` — updates local score and appends to a durable outbox.
5. `flush()` — replays pending events to remote `database` using idempotent event IDs.
6. `refresh()` — fetches a fresh snapshot from remote, atomically swaps, reapplies pending local events.

### Planned API

```python
from nl_processing.database_cache.service import DatabaseCacheService
from nl_processing.core.models import Language, PartOfSpeech, Word
from datetime import timedelta

cache = DatabaseCacheService(
    user_id="alex",
    source_language=Language.NL,
    target_language=Language.RU,
    exercise_types=["nl_to_ru", "multiple_choice"],
    cache_ttl=timedelta(minutes=30),
)

status = await cache.init()
pairs = await cache.get_words(word_type=PartOfSpeech.NOUN, limit=10, random=True)
scored = await cache.get_word_pairs_with_scores()

await cache.record_exercise_result(
    source_word=Word(normalized_form="fiets", word_type=PartOfSpeech.NOUN, language=Language.NL),
    exercise_type="nl_to_ru",
    delta=-1,
)

await cache.flush()
```

### Relationship to Other Modules

- **`database`** — authoritative remote store; `database_cache` consumes its export/sync APIs.
- **`sampling`** — should use `database_cache` as its hot-path data source for score-aware sampling.
- **`CachedDatabaseService`** (legacy) — superseded by `database_cache`; retained for backward compatibility.

## Development

```bash
uv sync                # install dependencies
make check             # full lint + test pipeline
uv run pytest tests/unit   # unit tests only (free, no API key)
```

See [docs/ENV_VARS.md](docs/ENV_VARS.md) for required environment variables and [NEON.md](NEON.md) for database setup.

## Contributing

See [docs/REALEASE_WORKFLOW.md](docs/REALEASE_WORKFLOW.md) for the release process and publishing considerations.
