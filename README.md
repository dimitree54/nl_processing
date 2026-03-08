# nl_processing

[![PyPI](https://img.shields.io/pypi/v/nl_processing)](https://pypi.org/project/nl_processing/)

Dutch language processing toolkit organized as a multi-package Python repository.

## Install

```bash
pip install nl_processing
```

The published `nl_processing` package is the aggregate build from the repo root. Day-to-day development happens inside the package folders under `packages/`.

## Repository Layout

```text
packages/
  core/
  extract_text_from_image/
  extract_words_from_text/
  translate_text/
  translate_word/
  database/
  database_cache/
  sampling/
docs/
pyproject.toml        # aggregate build for the published nl_processing package
Makefile              # repo-wide lint/test entrypoint
```

Each package has its own:

- `pyproject.toml`
- `ruff.toml`
- `pytest.ini`
- `tests/`
- `docs/`

## Modules

| Module | Class | Description | Docs |
|---|---|---|---|
| `core` | N/A | Shared models, exceptions, prompt helpers | [docs](packages/core) |
| `extract_text_from_image` | `ImageTextExtractor` | Extract Dutch text from images via Vision API | [docs](packages/extract_text_from_image/docs/) |
| `extract_words_from_text` | `WordExtractor` | Extract and normalize words from markdown text | [docs](packages/extract_words_from_text/docs/) |
| `translate_text` | `TextTranslator` | Translate text (NL -> RU) with markdown preservation | [docs](packages/translate_text/docs/) |
| `translate_word` | `WordTranslator` | Batch-translate words (NL -> RU) | [docs](packages/translate_word/docs/) |
| `database` | `DatabaseService` | Remote persistence for words, translations, and exercise scores | [docs](packages/database/docs/) |
| `database_cache` | `DatabaseCacheService` | Local-first SQLite cache over the remote database module | [docs](packages/database_cache/docs/) |
| `sampling` | `WordSampler` | Weighted word sampling with adversarial distractors | [docs](packages/sampling/docs/) |

## Development

Work inside one package when you only touch one module:

```bash
cd packages/translate_word
uv sync --all-groups
uv run pytest tests/unit
```

Run the repo-wide quality gate from the root:

```bash
make check
```

Useful package-local examples:

```bash
cd packages/core
uv run pytest tests/unit/core

cd packages/database
doppler run -- uv run pytest tests/integration/database
```

## Dependency Rule

Modules are independent packages. Cross-module dependencies must be explicit in the consuming package's `pyproject.toml`.

One intentional design change in this layout: `database` no longer imports `translate_word` directly. If you want automatic translation on `add_words()`, compose it explicitly:

```python
from nl_processing.core.models import Language
from nl_processing.database.service import DatabaseService
from nl_processing.translate_word.service import WordTranslator

db = DatabaseService(
    user_id="alex",
    translator=WordTranslator(
        source_language=Language.NL,
        target_language=Language.RU,
    ),
)
```

## Docs

- Shared overview: [docs/product-brief.md](docs/product-brief.md)
- Shared requirements: [docs/prd.md](docs/prd.md)
- Shared architecture: [docs/architecture.md](docs/architecture.md)
- Environment variables: [docs/ENV_VARS.md](docs/ENV_VARS.md)
- Release workflow: [docs/REALEASE_WORKFLOW.md](docs/REALEASE_WORKFLOW.md)
