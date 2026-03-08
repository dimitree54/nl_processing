---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-03-02'
inputDocuments:
  - docs/planning-artifacts/product-brief.md
  - docs/planning-artifacts/prd.md
  - nl_processing/extract_text_from_image/docs/product-brief-extract_text_from_image-2026-03-01.md
  - nl_processing/extract_text_from_image/docs/prd_extract_text_from_image.md
  - nl_processing/extract_words_from_text/docs/product-brief-extract_words_from_text-2026-03-01.md
  - nl_processing/extract_words_from_text/docs/prd_extract_words_from_text.md
  - nl_processing/translate_text/docs/product-brief-translate_text-2026-03-01.md
  - nl_processing/translate_text/docs/prd_translate_text.md
  - nl_processing/translate_word/docs/product-brief-translate_word-2026-03-01.md
  - nl_processing/translate_word/docs/prd_translate_word.md
workflowType: 'architecture'
project_name: 'nl_processing'
user_name: 'Dima'
date: '2026-03-02'
scope: 'shared-core'
---

# Architecture Decision Document — nl_processing (Shared Core)

_This document covers shared architectural decisions for the `nl_processing` project — the `core` package, cross-cutting patterns, and project-level conventions. Module-specific architectural decisions are documented in each module's architecture document and referenced from here._

> **Module architecture documents:**
> - [`extract_text_from_image`](../../nl_processing/extract_text_from_image/docs/architecture_extract_text_from_image.md)
> - [`extract_words_from_text`](../../nl_processing/extract_words_from_text/docs/architecture_extract_words_from_text.md)
> - [`translate_text`](../../nl_processing/translate_text/docs/architecture_translate_text.md)
> - [`translate_word`](../../nl_processing/translate_word/docs/architecture_translate_word.md)
> - [`database`](../../nl_processing/database/docs/architecture_database.md)

---

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

The project defines 20 core FRs (CFR1-20) for the `core` package and 14 shared FRs (SFR1-14) for all pipeline modules. Architecturally, the requirements break down into:

- **Public Interface Pydantic Models (CFR7-11):** `ExtractedText`, `Word`, `PartOfSpeech` enum, `Language` enum — defined in `core`. **Important:** only models that form public module interfaces (input/output contracts) live in `core`. Internal models (e.g., intermediate schemas used within a module's LangChain chain) remain in the module.
- **Exceptions (CFR12-15):** `APIError`, `TargetLanguageNotFoundError`, `UnsupportedImageFormatError` — centralized in `core`.
- **Prompt Management (CFR16-20):** Prompt loading utility in `core`; prompt content per-module. Prompt authoring helper as a dev-time script.
- **Shared Module Patterns (SFR1-14):** Structured output enforcement, zero-config defaults, Language enum interface, error wrapping, documentation conventions.

Each module adds 9-14 module-specific FRs covering its domain logic (see module architecture documents).

**Non-Functional Requirements:**

- 3 core NFRs (CNFR1-3): core is internal-only, has own tests
- 9 shared NFRs (SNFR1-9): OPENAI_API_KEY only, internal modules (no PyPI), type hints, 100% test pass rate, project-level dependency management
- Module-specific NFRs: performance targets vary (1s for image extraction, 5s for text processing, <1s for word translation batch, ≤200ms for database operations)

**Scale & Complexity:**

- Primary domain: Python library (internal modules, no web/mobile/API surface)
- Complexity level: Medium — quality validation and benchmarking required, no regulatory/compliance concerns
- Architectural components: 6 packages (`core` + 5 modules), each with clear boundaries

### Technical Constraints & Dependencies

- **Python 3.12+** — minimum runtime
- **LangChain + langchain-openai** — used directly by all modules (not isolated in core)
- **Pydantic >=2.0** — structured output enforcement and public interface models
- **OPENAI_API_KEY** — only external configuration (via `os.environ[]`, never `os.getenv`), managed via Doppler
- **opencv-python** — module-specific dependency for `extract_text_from_image` only
- **asyncpg** — module-specific dependency for `database` only (async PostgreSQL driver for Neon)
- **Project state:** Greenfield (scaffold/stubs only — no implementation exists yet)
- **Build tooling:** `pyproject.toml` with `uv` package manager — already initialized

### Cross-Cutting Concerns

1. **Error propagation:** Each module wraps upstream API errors as `APIError` from `core` — consistent typed exceptions for callers
2. **Model configurability:** Every module accepts optional `model` parameter (baseline: GPT-5 Mini; default: cheapest model that passes quality gates, currently targeting `gpt-5-nano`) — each module instantiates its own ChatOpenAI
3. **Language extensibility:** `Language` enum + per-module prompt JSONs — adding a language is a linguistic task, not engineering
4. **Prompt loading:** Shared utility in core for loading ChatPromptTemplate-format JSON files; content per-module
5. **Testing patterns:** Each module has different validation approach (exact match, set comparison, structural comparison) but shares the pattern of curated test cases as quality gate

---

## Starter Template Evaluation

**Not applicable.** This project is a Python library (internal modules), not a web/mobile/CLI application. The project is already initialized with `pyproject.toml` and `uv` package manager. There is no starter template or scaffolding CLI to evaluate. The directory structure and package layout are already established.

---

## Core Architectural Decisions

### Decision: No Engine Abstraction — Modules Use LangChain Directly

**Decision:** There is no shared "prompt execution engine" wrapping LangChain. Each module builds and executes its own LangChain chains directly using LangChain's built-in interfaces (`ChatOpenAI`, `ChatPromptTemplate`, tool calling via `bind_tools(...)`, chain composition via `|` operator, etc.).

**Rationale:** A thin wrapper that merely forwards calls to LangChain adds indirection without value. LangChain already provides one-line chain execution, structured output binding, and composable chain interfaces. Wrapping these in a project-specific engine would:
- Add a layer that developers must learn on top of LangChain
- Restrict access to LangChain features (vision, streaming, tool calling) behind our abstraction
- Create maintenance burden to keep the wrapper aligned with LangChain API evolution

**Implication:** All modules depend on `langchain` and `langchain-openai` directly. The `core` package does **not** mediate LLM access.

**Note:** This is a deviation from the PRD requirements CFR1-6 and SNFR1/SNFR7/CNFR3, which specified that only `core` depends on LangChain. This architectural decision supersedes those requirements — the PRD will be updated to reflect this.

### Decision: Core Package = Shared Models + Exceptions + Helpers Only

**Decision:** `nl_processing/core/` provides:
1. **Public interface Pydantic models** — only models that form module input/output contracts
2. **Shared exceptions** — `APIError`, `TargetLanguageNotFoundError`, `UnsupportedImageFormatError`
3. **Helpers** — only where they genuinely simplify usage (e.g., prompt loading utility)
4. **Scripts** — dev-time-only tools (prompt authoring helper) in a `scripts/` subdirectory

**What core does NOT provide:**
- No LLM engine or LangChain wrapper
- No internal/intermediate Pydantic models (these stay in their respective modules)
- No runtime orchestration or chain composition

### Decision: Core Package Structure (Flat)

```
nl_processing/core/
├── __init__.py          # empty (ruff strictly-empty-init-modules)
├── models.py            # PUBLIC interface models: ExtractedText, Word, PartOfSpeech, Language
├── exceptions.py        # APIError, TargetLanguageNotFoundError, UnsupportedImageFormatError
├── prompts.py           # prompt loading utility (load ChatPromptTemplate-format JSON)
└── scripts/
    └── prompt_author.py # dev-time prompt authoring helper (not runtime)
```

- 3 runtime code files — well within the ≤10 file limit
- Flat structure, no sub-packages
- `scripts/` is not a Python package — it contains standalone dev tools
- Consumers import explicitly: `from nl_processing.core.models import Language`

### Decision: Prompt JSON Format — LangChain ChatPromptTemplate Serialization

**Decision:** Prompt JSON files use the format produced by LangChain's `ChatPromptTemplate` serializer. No custom format.

**Rationale:** Using LangChain's native serialization means prompts can be loaded with `ChatPromptTemplate` built-in deserialization — no custom parsing needed. The `core` prompt loading helper wraps this for convenience but does not invent a new format.

**Implementation status:** The current `nl_processing.core.prompts.load_prompt()` implementation is temporarily based on a simplified `{ "messages": [[role, template], ...] }` JSON shape. This is non-compliant with this decision and will be corrected by migrating prompt saving/loading to LangChain native serialization.

### Decision: Module Internal Structure (Standard Layout)

Every pipeline module follows this structure:

```
nl_processing/<module_name>/
├── __init__.py          # empty
├── service.py           # public class (ImageTextExtractor, WordExtractor, etc.)
├── prompts/
│   └── nl.json          # language-specific prompt (ChatPromptTemplate format)
└── docs/
    ├── planning-artifacts/   # or just docs/ — existing per-module convention
    │   ├── product-brief-<module>-<date>.md
    │   ├── prd_<module>.md
    │   └── architecture_<module>.md
    └── ...
```

Additional files as needed per module (e.g., internal models, chain definitions), but `service.py` is always the public entry point.

For module-specific internal structure decisions (e.g., how `extract_text_from_image` handles image encoding, how `translate_word` handles batch processing), see each module's architecture document.

### Decision: Error Handling Pattern

Each module is responsible for wrapping upstream LangChain/OpenAI exceptions into `APIError` from `core`. The pattern:

```python
from nl_processing.core.exceptions import APIError

try:
    result = chain.invoke(input_data)
except Exception as e:
    raise APIError(str(e)) from e
```

Module-specific exceptions (`TargetLanguageNotFoundError`, `UnsupportedImageFormatError`) are raised by module logic, not by error wrapping. These are domain-level decisions, not API failure recovery.

### Decision: Each Module Instantiates Its Own ChatOpenAI

**Decision:** Each module's public class constructor creates its own `ChatOpenAI` instance. There is no shared or singleton LLM client.

**Rationale:** Modules may need different model configurations (e.g., vision model for image extraction vs text model for translation). We start with GPT-5 Mini as a baseline during evaluation, then downgrade to the cheapest model that still passes module quality gates. Constructor accepts optional `model` parameter; current default target is `gpt-5-nano`.

---

## Code Style & Quality Architecture

### Tooling Stack (Already Configured)

| Tool | Purpose | Configuration |
|---|---|---|
| **ruff** | Format + lint | `ruff.toml` (preview mode, line-length=120) |
| **pylint** | Module size enforcement (200-line max) + bad builtins check | Via Makefile |
| **vulture** | Dead code detection | Via Makefile |
| **jscpd** | Code duplication detection | Via Makefile |
| **pytest** | Testing (+ pytest-asyncio, pytest-xdist) | `pyproject.toml` |

### Quality Gate: `make check`

All code changes must pass `make check` before being considered complete:

```
make check  →  ruff format → ruff check --fix → pylint (200-line, bad builtins)
              → vulture → jscpd → pytest unit → pytest integration → pytest e2e
```

### Enforced Code Policies

**File size & modularity:**
- Strict 200-line per file limit (enforced by pylint). If hit → decompose, never compact.
- ≤10 code files per module (sub-modules don't count). If exceeded → group into sub-modules.
- ≤10 test files per test directory. If exceeded → group into sub-test folders.

**No silent fallbacks:**
- `os.environ['KEY']` only — never `os.getenv()`, `os.environ.get()`, or `os.environ.setdefault()`
- `dict['key']` preferred over `dict.get('key', default)` — fail loudly on unexpected state
- No introducing default values or fallback code branches without explicit approval

**No hiding problems:**
- Fix linter warnings — `noqa` is last resort, requires explicit user approval with explanation
- Test skipping is banned: no `pytest.skip()`, `@pytest.mark.skip`, `@pytest.mark.skipif` (enforced by ruff ban)
- Flaky tests: fix the flakiness, never skip

**Type hints:**
- All functions must have type hints
- Banned: `Any`, `object` as types, `cast()` (enforced by ruff)
- Use specific types, `Union`/`|`, constrained generics
- Don't over-engineer types — no new types/dataclasses/aliases just to satisfy type checker

**Import discipline:**
- No relative imports (enforced by ruff `ban-relative-imports = "all"`)
- No `unittest` — use pytest (enforced by ruff ban)
- No `__future__` imports (enforced by ruff ban)
- Empty `__init__.py` files (enforced by ruff `strictly-empty-init-modules`)

**Zero-legacy policy:**
- No backward compatibility maintenance
- Refactoring allowed if it improves architecture and doesn't break functionality
- No keeping old code or outdated interfaces after refactoring

**Environment variables & secrets:**
- All env vars managed via **Doppler CLI** — no `.env` files, no `.env.template` files
- All commands requiring env vars run with `doppler run --` prefix
- All env vars documented in `docs/ENV_VARS.md`
- See "Secrets Management" section below for full details

---

## Implementation Patterns & Consistency Rules

### Naming Conventions

**Python code (enforced by ruff N8xx rules):**
- Classes: `PascalCase` — `ImageTextExtractor`, `Word`, `APIError`
- Functions/methods: `snake_case` — `extract_from_path`, `load_prompt`
- Variables: `snake_case` — `source_language`, `prompt_messages`
- Constants: `UPPER_SNAKE_CASE` — `DEFAULT_MODEL`
- Private members: `_single_leading_underscore`

**Files and directories:**
- Python files: `snake_case.py` — `service.py`, `models.py`, `exceptions.py`
- Module directories: `snake_case` — `extract_text_from_image`, `translate_word`
- Prompt files: `<language_code>.json` — `nl.json`, `ru.json`

### Module Public Interface Pattern

Every module has exactly one public class in `service.py`. `__init__.py` remains empty (enforced by ruff `strictly-empty-init-modules`). Callers import directly from `service`:

```python
# Caller imports directly from service.py — no __init__.py re-export
from nl_processing.extract_text_from_image.service import ImageTextExtractor
from nl_processing.extract_words_from_text.service import WordExtractor
from nl_processing.translate_text.service import TextTranslator
from nl_processing.translate_word.service import WordTranslator
from nl_processing.database.service import DatabaseService
```

The public class follows this pattern:

```python
# nl_processing/<module>/service.py

class <ModuleName>:
    def __init__(self, *, language: Language = Language.NL, model: str = "gpt-5-nano") -> None:
        ...

    def <primary_method>(self, input_data: <InputType>) -> <OutputType>:
        ...
```

- Constructor: keyword-only args, all optional with defaults
- One primary method (two for `extract_text_from_image`: `extract_from_path`, `extract_from_cv2`)
- Return types use `core` public models where applicable

### Error Handling Pattern

**Two categories of exceptions, same `core` import path:**

1. **`APIError`** — wraps upstream LangChain/OpenAI failures. Every module raises this for API errors. Callers catch `APIError` for all API-related failures regardless of module.

2. **Module-specific exceptions** (`TargetLanguageNotFoundError`, `UnsupportedImageFormatError`) — raised by module domain logic. Defined in `core.exceptions` for single import path, but semantically belong to the module that raises them.

**Pattern for callers:**
```python
try:
    result = extractor.extract_from_path("image.png")
except TargetLanguageNotFoundError:
    # domain-specific handling
except APIError:
    # upstream API failure handling
```

### Prompt File Organization

Each module stores its own prompt files in `<module>/prompts/<language_code>.json`. Adding a new language = adding a new JSON file + test cases. No code changes to module logic.

The `core.prompts` helper provides a `load_prompt(module_path, language_code)` utility that resolves the file path and returns a `ChatPromptTemplate`. Modules may also load prompts directly using LangChain if the helper doesn't add value for their use case.

### Test Organization

```
tests/
├── unit/
│   ├── core/
│   ├── extract_text_from_image/
│   ├── extract_words_from_text/
│   ├── translate_text/
│   └── translate_word/
├── integration/
│   ├── core/
│   ├── extract_text_from_image/
│   ├── extract_words_from_text/
│   ├── translate_text/
│   └── translate_word/
└── e2e/
    ├── extract_text_from_image/
    ├── extract_words_from_text/
    ├── translate_text/
    └── translate_word/
```

- Modularized at all test levels (unit, integration, e2e)
- ≤10 test files per directory — group into sub-folders if exceeded
- Unit tests: mock LLM calls, test module logic in isolation
- Integration tests: real API calls, validate prompt quality and structured output
- E2e tests: full pipeline scenarios

### Enforcement

All patterns are enforced by `make check` (ruff, pylint, vulture, jscpd, pytest). No manual review required for mechanical rules — the toolchain catches violations automatically.

---

## Project Structure & Boundaries

### Complete Project Directory Structure

```
nl_processing/                          # project root
├── pyproject.toml                      # project metadata, dependencies, build config
├── ruff.toml                           # ruff linter/formatter configuration
├── Makefile                            # make check (format → lint → test pipeline)
├── pytest.ini                          # pytest configuration
├── vulture_whitelist.py                # vulture dead-code exceptions
├── .jscpd.json                         # copy-paste detection config
├── .doppler.yaml                       # Doppler CLI project/environment config (tracked in git)
├── README.md
├── uv.lock
│
├── docs/
│   ├── ENV_VARS.md                     # all environment variables documentation
│   └── planning-artifacts/             # SHARED planning docs (project-level)
│       ├── product-brief.md
│       ├── prd.md
│       └── architecture.md             # THIS DOCUMENT
│
├── nl_processing/                      # source package
│   ├── __init__.py                     # empty
│   │
│   ├── core/                           # shared infrastructure package
│   │   ├── __init__.py                 # empty
│   │   ├── models.py                   # PUBLIC interface Pydantic models + Language enum
│   │   ├── exceptions.py               # APIError, TargetLanguageNotFoundError, UnsupportedImageFormatError
│   │   ├── prompts.py                  # prompt loading helper (ChatPromptTemplate JSON)
│   │   └── scripts/                    # dev-time-only tools (NOT a Python package)
│   │       └── prompt_author.py        # prompt authoring helper
│   │
│   ├── extract_text_from_image/        # module 1: image → markdown text
│   │   ├── __init__.py                 # empty
│   │   ├── service.py                  # ImageTextExtractor (public class)
│   │   ├── prompts/
│   │   │   └── nl.json                 # Dutch extraction prompt
│   │   └── docs/                       # module-specific planning docs
│   │       ├── product-brief-extract_text_from_image-2026-03-01.md
│   │       ├── prd_extract_text_from_image.md
│   │       └── architecture_extract_text_from_image.md
│   │
│   ├── extract_words_from_text/        # module 2: markdown text → word objects
│   │   ├── __init__.py                 # empty
│   │   ├── service.py                  # WordExtractor (public class)
│   │   ├── prompts/
│   │   │   └── nl.json                 # Dutch word extraction prompt
│   │   └── docs/
│   │       ├── product-brief-extract_words_from_text-2026-03-01.md
│   │       ├── prd_extract_words_from_text.md
│   │       └── architecture_extract_words_from_text.md
│   │
│   ├── translate_text/                 # module 3: text → translated text
│   │   ├── __init__.py                 # empty
│   │   ├── service.py                  # TextTranslator (public class)
│   │   ├── prompts/
│   │   │   └── nl_ru.json              # Dutch→Russian translation prompt
│   │   └── docs/
│   │       ├── product-brief-translate_text-2026-03-01.md
│   │       ├── prd_translate_text.md
│   │       └── architecture_translate_text.md
│   │
│   ├── translate_word/                 # module 4: word list → translation results
│   │   ├── __init__.py                 # empty
│   │   ├── service.py                  # WordTranslator (public class)
│   │   ├── prompts/
│   │   │   └── nl_ru.json              # Dutch→Russian word translation prompt
│   │   └── docs/
│   │       ├── product-brief-translate_word-2026-03-01.md
│   │       ├── prd_translate_word.md
│   │       └── architecture_translate_word.md
│   │
│   └── database/                       # module 5: async persistence layer
│       ├── __init__.py                 # public exports: DatabaseService, CachedDatabaseService
│       ├── service.py                  # DatabaseService, CachedDatabaseService (public classes)
│       ├── backend/
│       │   ├── __init__.py
│       │   ├── abstract.py             # AbstractBackend (ABC)
│       │   └── neon.py                 # NeonBackend (asyncpg implementation)
│       ├── models.py                   # AddWordsResult, WordTranslationPair (module-internal models)
│       ├── exceptions.py               # ConfigurationError, DatabaseError
│       ├── logging.py                  # Structured logging setup
│       ├── testing.py                  # Test utilities: drop_all_tables, reset_database (NOT production)
│       └── docs/
│           ├── product-brief-database-2026-03-02.md
│           ├── prd_database.md
│           └── architecture_database.md
│
└── tests/
    ├── __init__.py
    ├── unit/
    │   ├── __init__.py
    │   ├── core/                       # core unit tests
    │   ├── extract_text_from_image/    # module 1 unit tests
    │   ├── extract_words_from_text/    # module 2 unit tests
    │   ├── translate_text/             # module 3 unit tests
    │   ├── translate_word/             # module 4 unit tests
    │   └── database/                   # module 5 unit tests
    ├── integration/
    │   ├── __init__.py
    │   ├── core/
    │   ├── extract_text_from_image/
    │   ├── extract_words_from_text/
    │   ├── translate_text/
    │   ├── translate_word/
    │   └── database/
    └── e2e/
        ├── __init__.py
        ├── conftest.py
        ├── extract_text_from_image/
        ├── extract_words_from_text/
        ├── translate_text/
        ├── translate_word/
        └── database/
```

### Documentation Organization Principle

**Rule:** All documentation related to a specific module lives in `<module>/docs/`. All shared/project-level documentation lives in `docs/planning-artifacts/`. No duplication between shared and module-specific docs — they cross-reference each other.

| Doc type | Shared (project-level) | Module-specific |
|---|---|---|
| Product brief | `docs/planning-artifacts/product-brief.md` | `<module>/docs/product-brief-<module>-<date>.md` |
| PRD | `docs/planning-artifacts/prd.md` | `<module>/docs/prd_<module>.md` |
| Architecture | `docs/planning-artifacts/architecture.md` | `<module>/docs/architecture_<module>.md` |

### Architectural Boundaries

**Package boundary: `core` ↔ modules**
- `core` knows nothing about modules — it provides models, exceptions, and utilities
- Modules import from `core` (models, exceptions, optionally prompt loader)
- Modules import from `langchain`/`langchain-openai` directly for chain building
- Modules never import from each other — they are independently usable. **Exception:** `database` has a direct dependency on `translate_word` for automatic translation of newly added words (intentional — `database` is a persistence/orchestration layer)

**Module boundary: module ↔ caller**
- Each module has exactly one public class in `service.py` (imported directly, no `__init__.py` re-export)
- All input/output types are `core` public models or Python builtins (`str`, `list[str]`)
- All exceptions come from `core.exceptions`
- No internal implementation details leak through the public interface

**Test boundary: strict per-module isolation**
- Each test directory (`unit/<module>/`, `integration/<module>/`, `e2e/<module>/`) tests only that module
- No cross-module test dependencies
- Unit tests mock LLM calls — no real API calls
- Integration tests make real API calls — validate prompt quality
- E2e tests validate full pipeline scenarios

### Data Flow

```
Image → [extract_text_from_image] → markdown text
         markdown text → [extract_words_from_text] → list[Word]
         markdown text → [translate_text] → translated text
         list[Word] → [translate_word] → list[Word]

         list[words] + user_id → [database] → word-translation pairs, feedback
                                     ↓ (async, fire-and-forget)
                                 [translate_word] → translations stored back
```

Each module is independently callable. The pipeline is composable — the caller connects modules, not the modules themselves. The `database` module is the only module that directly depends on another module (`translate_word`) — it acts as a persistence and orchestration layer that triggers translation of new words asynchronously.

### Prompt File Naming Convention

| Module | Prompt file pattern | Example |
|---|---|---|
| Single-language modules | `<language_code>.json` | `nl.json` |
| Translation modules | `<source>_<target>.json` | `nl_ru.json` |

---

## Secrets Management — Doppler

### Decision: Doppler CLI for All Environment Variables

**Decision:** All environment variables and secrets are managed via Doppler CLI. No `.env` files, no `.env.template` files, no `load_dotenv`.

**Rationale:** Centralized secrets management with environment separation (dev/stg/prd), automatic injection via `doppler run --`, and no risk of committing secrets to git.

### Doppler Configuration

- **Project name:** `nl_processing`
- **Environments:** `dev`, `stg`, `prd`
- **Config file:** `.doppler.yaml` in project root (tracked in git)

### Environment Separation for Database

Each Doppler environment has its own `DATABASE_URL` pointing to a separate Neon database:

| Doppler Env | Database | Purpose |
|---|---|---|
| `dev` | `nl_processing_dev` | Development + all automated tests. Ephemeral — freely wiped by tests. |
| `stg` | `nl_processing_stg` | Pre-production validation. Stable — not wiped by tests. |
| `prd` | `nl_processing_prd` | Production data. Stable — never touched by tests. |

All `make check` and CI runs use the `dev` environment. See `database` module architecture for full testing strategy.

### Running Commands

All commands that require environment variables must use `doppler run --`:

```bash
# Tests
doppler run -- uv run pytest -n auto tests/unit
doppler run -- uv run pytest -n auto tests/integration
doppler run -- uv run pytest -n auto tests/e2e

# Any command needing env vars
doppler run -- <command>
```

### Makefile Integration

`make check` must run under `doppler run --` to provide `OPENAI_API_KEY` for integration/e2e tests:

```bash
# Full check with Doppler
doppler run -- make check
```

### Environment Variables

All env vars are documented in `docs/ENV_VARS.md`.

| Variable | Type | Description | Set by |
|---|---|---|---|
| `OPENAI_API_KEY` | Secret | OpenAI API authentication key | Developer (via Doppler) |
| `DATABASE_URL` | Secret | Neon PostgreSQL connection string (used by `database` module) | Developer (via Doppler) |

### Adding New Variables

- **Non-secret** (ports, model names, timeouts): set autonomously via `doppler secrets set -p nl_processing -c <env> KEY=value` in all 3 environments
- **Secret** (API keys, tokens): request developer to set via Doppler, then validate with `doppler secrets --only-names`
- **Always** document in `docs/ENV_VARS.md` after adding
- **Never** include environment name in variable name (no `TEST_` prefix, no `_PROD` suffix) — use Doppler environments for separation

### Code Pattern

```python
import os

# Correct — fail loudly if not configured
api_key = os.environ["OPENAI_API_KEY"]

# WRONG — silent fallback (banned by ruff)
# api_key = os.getenv("OPENAI_API_KEY", "default")
```

---

## CI/CD & Test Execution Policy

### Decision: GitHub Actions Runs All Tests on PR to Master

**Decision:** A GitHub Actions workflow triggers on every PR to `master` and runs the full `make check` pipeline — including integration and e2e tests that make real (paid) API calls.

**Rationale:** Integration tests validate prompt quality and API compatibility — they are the primary quality gate for LLM-powered modules. Skipping them on PR would allow prompt regressions to reach master.

### GitHub Actions Configuration

```yaml
# .github/workflows/ci.yml
name: CI
on:
  pull_request:
    branches: [master]

jobs:
  check:
    runs-on: ubuntu-latest
    environment: ci  # Doppler syncs secrets to this GitHub environment
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - name: Install Doppler CLI
        run: |
          curl -sLf --retry 3 --tlsv1.2 --proto "=https" 'https://packages.doppler.com/public/cli/gpg.DE2A7741A397C129.key' | sudo gpg --dearmor -o /usr/share/keyrings/doppler-archive-keyring.gpg
          echo "deb [signed-by=/usr/share/keyrings/doppler-archive-keyring.gpg] https://packages.doppler.com/public/cli/deb/debian any-version main" | sudo tee /etc/apt/sources.list.d/doppler-cli.list
          sudo apt-get update && sudo apt-get install -y doppler
      - name: Install dependencies
        run: uv sync --all-groups
      - name: Run full check
        run: doppler run -- make check
        env:
          DOPPLER_TOKEN: ${{ secrets.DOPPLER_TOKEN }}
```

**Doppler GitHub integration:** Doppler's native GitHub sync pushes secrets to the `ci` GitHub environment. The `DOPPLER_TOKEN` service token is the only secret manually configured in GitHub.

### Test Execution Policy

**After every completed task:**
1. Run `doppler run -- make check` locally
2. All test levels must pass: unit → integration → e2e
3. Integration tests make real API calls (paid) — **they must not be skipped**
4. If integration tests fail due to prompt changes, fix the prompt before considering the task complete

**On PR to master:**
- GitHub Actions runs the full `make check` pipeline automatically
- PR cannot be merged if any test level fails
- Integration/e2e tests run with real API calls using Doppler-provided secrets

**Cost awareness:**
- Integration/e2e tests are paid (OpenAI API calls) and slower than unit tests
- This cost is acceptable and necessary — prompt quality is the primary product quality metric
- Unit tests should mock LLM calls to keep the fast feedback loop for logic changes

---

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
- "No engine wrapper" + "modules use LangChain directly" — consistent. Core provides only models, exceptions, and helpers.
- Empty `__init__.py` (ruff rule) + direct imports from `service.py` — consistent. No re-export conflict.
- Prompt loading helper in core + ChatPromptTemplate native format — consistent. No custom format to maintain.
- Module-independent architecture + composable pipeline — consistent. Caller connects modules, not internal wiring.

**Pattern Consistency:**
- Naming conventions (PascalCase classes, snake_case files/functions) — consistently applied across all 5 packages.
- Error handling pattern (APIError wrapping + module-specific domain exceptions) — consistent across all 4 modules.
- Constructor pattern (keyword-only args, optional with defaults) — consistent, except translation modules require source+target language (intentional difference).

**Structure Alignment:**
- Project tree supports all decisions: core/ is flat, modules follow standard layout, tests are modularized.
- Documentation organization (shared in `docs/planning-artifacts/`, module-specific in `<module>/docs/`) — consistent, no duplication.

### Requirements Coverage ✅

**Functional Requirements Coverage:**

| Requirement | Architecture Support |
|---|---|
| CFR7-11 (Pydantic models) | `core/models.py` — `ExtractedText`, `Word`, `PartOfSpeech` enum, `Language` enum |
| CFR12-15 (Exceptions) | `core/exceptions.py` |
| CFR16-20 (Prompt management) | `core/prompts.py` + `core/scripts/prompt_author.py` |
| SFR1-2 (Structured output) | Each module uses LangChain tool calling (recommended: `bind_tools(...)` + `tool_calls`) to enforce schemas |
| SFR3-5 (Configuration) | Constructor pattern with defaults, model param |
| SFR6-8 (Language support) | Language enum + per-module prompt JSONs |
| SFR9-11 (Error handling) | APIError wrapping pattern + module-specific semantics |
| SFR12-14 (Documentation) | Docstrings + README convention |
| Module-specific FRs | Covered in each module's architecture document |

**Non-Functional Requirements Coverage:**

| Requirement | Architecture Support |
|---|---|
| CNFR1 (Core is internal) | ✅ Core has no public interface for callers |
| CNFR2 (Core tests) | ✅ `tests/unit/core/` defined |
| SNFR2 (OPENAI_API_KEY only) | ✅ `os.environ['OPENAI_API_KEY']` pattern |
| SNFR3 (Internal modules) | ✅ No PyPI publishing |
| SNFR4 (Type hints) | ✅ Enforced by ruff ANN rules |
| SNFR5 (100% test pass) | ✅ `make check` includes all test levels |
| SNFR6-9 (Dependencies) | ✅ Project-level management via pyproject.toml |
| Module-specific NFRs | Covered in each module's architecture document |

**PRD Alignment:**

The shared PRD has been updated to align with all architectural decisions. Engine requirements (former CFR1-6) removed, LangChain dependency rules updated (SNFR1, SNFR7), CNFR3 removed, Doppler secrets management added (SNFR10-16), testing policy added (SNFR17-19). No remaining deviations between architecture and PRD.

### Implementation Readiness ✅

**Decision Completeness:**
- All critical decisions documented: core structure, no engine, direct LangChain usage, prompt format, import pattern, error handling
- Code style policies fully specified with toolchain enforcement
- All patterns have concrete examples

**Structure Completeness:**
- Complete project tree with every file and directory
- Clear boundary definitions (core ↔ modules, module ↔ caller, test isolation)
- Documentation organization normalized across all modules

**Pattern Completeness:**
- Naming conventions, file structure, module interface pattern, error handling pattern, prompt organization, test organization — all specified

### Architecture Completeness Checklist

- [x] Project context analyzed (requirements, constraints, cross-cutting concerns)
- [x] Core architectural decisions documented (no engine, direct LangChain, core = models+exceptions+helpers)
- [x] Code style & quality architecture (ruff, pylint, vulture, jscpd, make check)
- [x] Implementation patterns (naming, imports, module interface, error handling, prompts)
- [x] Complete project directory structure
- [x] Architectural boundaries defined (core ↔ modules, module ↔ caller, test isolation)
- [x] Data flow documented
- [x] Module-specific decisions in separate documents (4 module architectures)
- [x] No duplication between shared and module-specific docs
- [x] PRD deviations documented with rationale
- [x] Validation complete

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High

**Key Strengths:**
- Simple, flat architecture — no unnecessary abstractions
- Strong enforcement via automated toolchain (make check)
- Clear separation: shared concerns in core, module-specific in modules, no duplication
- 5-document structure mirrors the project's 5-package structure

**Action Items Before Implementation:**
- ~~Update shared PRD to align with architecture~~ — DONE (engine requirements removed, LangChain rules updated, Doppler added, test policy added)
- Create `docs/ENV_VARS.md` documenting all environment variables
- Set up Doppler project `nl_processing` with `dev`/`stg`/`prd` environments
- Create `.doppler.yaml` in project root
- Create `.github/workflows/ci.yml` for PR-to-master CI pipeline
- Update `Makefile` to work with `doppler run --` for integration/e2e tests
