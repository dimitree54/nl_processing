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
| `database` | `DatabaseService` | Persist words and translations to Neon PostgreSQL | [docs](nl_processing/database/docs/) |
| `sampling` | `WordSampler` | Weighted word sampling with adversarial distractors | [docs](nl_processing/sampling/docs/) |

Each module's `docs/` folder contains a product brief, PRD, and architecture doc.

## Development

```bash
uv sync                # install dependencies
make check             # full lint + test pipeline
uv run pytest tests/unit   # unit tests only (free, no API key)
```

See [docs/ENV_VARS.md](docs/ENV_VARS.md) for required environment variables and [NEON.md](NEON.md) for database setup.

## Contributing

See [docs/REALEASE_WORKFLOW.md](docs/REALEASE_WORKFLOW.md) for the release process and publishing considerations.
