---
Task ID: `T2`
Title: `Migrate core prompt loading/saving to LangChain native dumpd()/load()`
Sprint: `2026-03-03_extract-text-v2-modifications`
Module: `core` (shared infrastructure)
Depends on: `T1`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Replace the custom prompt JSON format (`{"messages": [["role", "template"], ...]}`) with LangChain's native serialization (`dumpd()`/`load()`). This brings the codebase into compliance with the architecture decision CFR13 and eliminates custom parsing logic.

## Context (contract mapping)

- Architecture: `docs/planning-artifacts/architecture.md` § "Prompt JSON Format — LangChain ChatPromptTemplate Serialization" — "Prompt JSON files use the format produced by LangChain's ChatPromptTemplate serializer. No custom format."
- Architecture: same section — "Implementation status: The current nl_processing.core.prompts.load_prompt() implementation is temporarily based on a simplified format. This is non-compliant and will be corrected."
- Requirements: CFR16-20 (prompt management)

## Preconditions

- T1 is complete (test files no longer import `unittest.mock`).
- `langchain_core.load.dumpd` and `langchain_core.load.load` are available (verified: they exist in the installed `langchain-core` package).

## Non-goals

- Do not regenerate `nl.json` yet — that is T3. This task only changes the loading/saving mechanism. The `nl.json` file WILL need to be updated to the new format, but keep it minimal (convert the existing simple prompt to native format, without few-shot examples).
- Do not change the `load_prompt()` function signature or return type.
- Do not change `service.py`.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/core/prompts.py` — rewrite to use `langchain_core.load.load()`
- `nl_processing/core/scripts/prompt_author.py` — rewrite to use `langchain_core.load.dumpd()`
- `nl_processing/extract_text_from_image/prompts/nl.json` — convert to LangChain native format (without few-shot examples — that's T3)
- `tests/unit/core/test_prompts.py` — update test data and assertions for new format

**FORBIDDEN — this task must NEVER touch:**
- `nl_processing/core/models.py`, `nl_processing/core/exceptions.py`
- Any module's `service.py`
- Any module-level test files
- `pyproject.toml`, `ruff.toml`, `Makefile`

**Test scope:**
- Tests go in: `tests/unit/core/`
- Test command: `uv run pytest tests/unit/core/ -x -v`
- Also verify: `uv run pytest tests/unit/extract_text_from_image/ -x -v` (to confirm nl.json still loads)

## Touched surface (expected files / modules)

- `nl_processing/core/prompts.py` (46 lines → ~25 lines)
- `nl_processing/core/scripts/prompt_author.py` (60 lines → ~30 lines)
- `nl_processing/extract_text_from_image/prompts/nl.json` (6 lines → larger, LangChain format)
- `tests/unit/core/test_prompts.py` (134 lines — update test data format)

## Dependencies and sequencing notes

- Depends on T1 because both T1 and T2 affect the test baseline. T1 fixes lint, T2 changes the format that tests validate.
- T3 depends on T2 because T3 will use the new `prompt_author.py` to generate `nl.json` with few-shot examples.

## Third-party / library research (mandatory for any external dependency)

### `langchain_core.load.dumpd()`

- **Library**: `langchain-core` (version `>=0.3,<1` — pinned in `pyproject.toml`)
- **Import**: `from langchain_core.load import dumpd`
- **Documentation**: https://python.langchain.com/api_reference/core/load/langchain_core.load.dump.dumpd.html
- **API**: `dumpd(obj: Serializable) -> dict` — serializes a LangChain `Serializable` object to a dict. `ChatPromptTemplate` extends `Serializable`.
- **Verified usage** (tested locally):
  ```python
  from langchain_core.load import dumpd
  from langchain_core.prompts import ChatPromptTemplate
  import json

  prompt = ChatPromptTemplate.from_messages([("system", "hello"), ("placeholder", "{images}")])
  data = dumpd(prompt)
  # data is a dict with keys: "lc", "type", "id", "kwargs"
  json.dumps(data, indent=2)  # serializable to JSON
  ```
- **Output format**:
  ```json
  {
    "lc": 1,
    "type": "constructor",
    "id": ["langchain", "prompts", "chat", "ChatPromptTemplate"],
    "kwargs": {
      "input_variables": [...],
      "messages": [...]
    }
  }
  ```

### `langchain_core.load.load()`

- **Library**: `langchain-core` (same package)
- **Import**: `from langchain_core.load import load`
- **Documentation**: https://python.langchain.com/api_reference/core/load/langchain_core.load.load.load.html
- **API**: `load(data: dict) -> Any` — deserializes a dict produced by `dumpd()` back into the original LangChain object. Returns a `ChatPromptTemplate` when the input was serialized from one.
- **Beta warning**: `load()` emits a `LangChainBetaWarning` on first use. This is cosmetic and does not affect functionality.
- **Verified usage** (tested locally):
  ```python
  from langchain_core.load import load, dumpd
  from langchain_core.prompts import ChatPromptTemplate

  prompt = ChatPromptTemplate.from_messages([("system", "hello"), ("placeholder", "{images}")])
  data = dumpd(prompt)
  prompt2 = load(data)
  # type(prompt2) == ChatPromptTemplate ✅
  # prompt2.input_variables == [] ✅ (placeholder doesn't add vars)
  ```
- **Known gotchas**:
  - `load()` emits `LangChainBetaWarning` — suppress in tests with `warnings.filterwarnings` or accept.
  - `load()` requires the classes referenced in the serialized data to be importable. Since we only use `langchain_core.prompts` classes, this is always true.

## Implementation steps (developer-facing)

### Step 1: Rewrite `nl_processing/core/prompts.py`

Replace the entire file content with:

```python
import json
from pathlib import Path

from langchain_core.load import load
from langchain_core.prompts import ChatPromptTemplate


def load_prompt(prompt_path: str) -> ChatPromptTemplate:
    """Load a ChatPromptTemplate from a LangChain-serialized JSON file.

    The JSON file must contain the output of `langchain_core.load.dumpd(prompt)`.

    Args:
        prompt_path: Path to the prompt JSON file in LangChain native format.

    Returns:
        A ChatPromptTemplate ready for chain composition.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
        ValueError: If the JSON file is malformed or cannot be deserialized.
    """
    path = Path(prompt_path)
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in prompt file {prompt_path}: {e}") from e

    if not isinstance(data, dict):
        raise TypeError(f"Prompt file must contain a JSON object, got {type(data).__name__}")

    try:
        prompt = load(data)
    except Exception as e:
        raise ValueError(f"Failed to deserialize ChatPromptTemplate from {prompt_path}: {e}") from e

    if not isinstance(prompt, ChatPromptTemplate):
        raise TypeError(
            f"Expected ChatPromptTemplate, got {type(prompt).__name__} from {prompt_path}"
        )

    return prompt
```

Key changes:
- Removed custom `"messages"` field validation and tuple conversion.
- Uses `langchain_core.load.load()` for deserialization.
- Added type check on the deserialized object.
- Removed the `TypeError` checks for `"messages"` field — no longer applicable.
- Kept `FileNotFoundError`, `ValueError` (malformed JSON), `TypeError` (not a dict).

### Step 2: Rewrite `nl_processing/core/scripts/prompt_author.py`

Replace the entire file content with:

```python
"""Prompt authoring helper — serialize ChatPromptTemplate to JSON.

Usage:
    1. Edit the `build_prompt()` function below to define your prompt.
    2. Set OUTPUT_PATH to your desired output file path.
    3. Run: uv run python nl_processing/core/scripts/prompt_author.py

The output JSON can be loaded by `nl_processing.core.prompts.load_prompt()`.
"""

import json

from langchain_core.load import dumpd
from langchain_core.prompts import ChatPromptTemplate


def build_prompt() -> ChatPromptTemplate:
    """Define your prompt here. Edit this function for each prompt you author."""
    return ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant. Respond in {language}."),
        ("human", "{input}"),
    ])


def serialize_prompt_to_json(prompt: ChatPromptTemplate, output_path: str) -> None:
    """Serialize a ChatPromptTemplate to JSON using LangChain native format.

    Args:
        prompt: The ChatPromptTemplate to serialize.
        output_path: Path where to save the JSON file.
    """
    data = dumpd(prompt)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


OUTPUT_PATH = "output_prompt.json"


if __name__ == "__main__":
    prompt = build_prompt()
    serialize_prompt_to_json(prompt, OUTPUT_PATH)
    print(f"Prompt saved to {OUTPUT_PATH}")  # noqa: T201 — dev script, print is intentional
```

Key changes:
- Replaced custom role-extraction logic (25+ lines) with single `dumpd(prompt)` call.
- Removed `hasattr` checks and class-name parsing.
- `serialize_prompt_to_json()` now takes the same arguments but uses `dumpd()` internally.

### Step 3: Convert `nl_processing/extract_text_from_image/prompts/nl.json`

Generate the new `nl.json` by running a one-off script (or by running the prompt_author interactively):

```python
from langchain_core.load import dumpd
from langchain_core.prompts import ChatPromptTemplate
import json

prompt = ChatPromptTemplate.from_messages([
    ("system", "Je bent een tekst-extractie assistent. Extraheer alleen de Nederlandse tekst uit het aangeboden beeld. Behoud de originele documentstructuur als markdown (koppen, nadruk, regelafbrekingen). Negeer tekst in andere talen. Retourneer alleen de geëxtraheerde tekst, zonder commentaar of uitleg."),
    ("placeholder", "{images}"),
])
data = dumpd(prompt)
with open("nl_processing/extract_text_from_image/prompts/nl.json", "w") as f:
    json.dump(data, f, indent=2)
```

The output will be in LangChain native format. This is an intermediate version — T3 will regenerate it with few-shot examples.

### Step 4: Update `tests/unit/core/test_prompts.py`

The existing tests create test prompt files in the OLD format (`{"messages": [["role", "template"]]}`). They must be updated to use the NEW format (LangChain native).

**For each test that creates a valid prompt file**, replace the test data:

Instead of:
```python
prompt_data = {"messages": [["system", "You are a helpful assistant."], ["human", "{input}"]]}
```

Use:
```python
from langchain_core.load import dumpd
prompt = ChatPromptTemplate.from_messages([("system", "You are a helpful assistant."), ("human", "{input}")])
prompt_data = dumpd(prompt)
```

**Tests to update:**

1. `test_load_prompt_valid_file` — use `dumpd()` to create test data
2. `test_load_prompt_round_trip` — use `dumpd()` for both creation and comparison
3. `test_load_prompt_empty_messages` — use `dumpd()` with empty messages
4. `test_load_prompt_complex_template` — use `dumpd()` with multiple message types

**Tests that remain unchanged:**

5. `test_load_prompt_missing_file` — still tests `FileNotFoundError`
6. `test_load_prompt_malformed_json` — still tests `ValueError` for bad JSON
7. `test_load_prompt_not_dict` — still tests `TypeError` for non-dict JSON

**Tests to update or remove:**

8. `test_load_prompt_missing_messages_field` — the old format had a `"messages"` key check. The new format checks via `load()`. This test should be changed to test a dict that is NOT a valid LangChain serialization (e.g., `{"other_field": "value"}`) — it should now raise `ValueError` from the `load()` call.
9. `test_load_prompt_messages_not_list` — same, update to test an invalid LangChain dict structure.
10. `test_load_prompt_invalid_message_format` — update to test a dict that looks like LangChain format but has invalid data.

**Import to add** at the top of the test file:
```python
from langchain_core.load import dumpd
```

### Step 5: Verify

1. Run `uv run ruff check nl_processing/core/prompts.py nl_processing/core/scripts/prompt_author.py`
2. Run `uv run pytest tests/unit/core/ -x -v` — all tests pass
3. Run `uv run pytest tests/unit/extract_text_from_image/ -x -v` — all tests pass (nl.json still loads correctly)
4. Verify the new `nl.json` loads correctly: `uv run python -c "from nl_processing.core.prompts import load_prompt; p = load_prompt('nl_processing/extract_text_from_image/prompts/nl.json'); print(type(p), p.input_variables)"`

## Production safety constraints (mandatory)

- No database operations.
- No shared resources affected.
- The production instance uses its own copy of the code. Changes to `nl.json` in this directory do not affect the production instance (running from a different directory).

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Using LangChain's built-in `dumpd()`/`load()` — eliminating custom code, not adding more.
- **Correct libraries only**: `langchain-core>=0.3,<1` — already in `pyproject.toml`.
- **Correct file locations**: All files in existing locations.
- **No regressions**: `load_prompt()` signature and return type are unchanged. All callers (`service.py`) continue to work.

## Error handling + correctness rules (mandatory)

- `load()` failures are caught and re-raised as `ValueError` with a descriptive message — no silent fallback.
- Type mismatch (loaded object is not `ChatPromptTemplate`) raises `TypeError`.
- `FileNotFoundError` and JSON decode errors preserved from the old implementation.

## Zero legacy tolerance rule (mandatory)

- The entire custom serialization logic in `prompt_author.py` (role extraction via class name parsing, `hasattr` checks) is **deleted**.
- The entire custom deserialization logic in `prompts.py` (messages field validation, tuple conversion, `from_messages`) is **deleted**.
- No commented-out code remains.
- The old format `{"messages": [["role", "template"]]}` is no longer supported — the file is converted to LangChain native format.

## Acceptance criteria (testable)

1. `nl_processing/core/prompts.py` uses `from langchain_core.load import load` and calls `load(data)` — no custom parsing
2. `nl_processing/core/scripts/prompt_author.py` uses `from langchain_core.load import dumpd` and calls `dumpd(prompt)` — no custom serialization
3. `nl_processing/extract_text_from_image/prompts/nl.json` contains LangChain native format (has `"lc": 1` key)
4. `load_prompt("nl_processing/extract_text_from_image/prompts/nl.json")` returns a `ChatPromptTemplate` with `{images}` placeholder
5. `uv run pytest tests/unit/core/ -x -v` — all tests pass
6. `uv run pytest tests/unit/extract_text_from_image/ -x -v` — all tests pass
7. No `"from_messages"` logic remains in `prompts.py` for deserialization
8. No `hasattr(msg, "prompt")` logic remains in `prompt_author.py`

## Verification / quality gates

- [ ] `uv run ruff check nl_processing/core/` — zero errors
- [ ] `uv run ruff check nl_processing/core/scripts/` — zero errors
- [ ] `uv run pytest tests/unit/core/ -x -v` — all tests pass
- [ ] `uv run pytest tests/unit/extract_text_from_image/ -x -v` — all tests pass (nl.json works)
- [ ] `uvx pylint nl_processing/core/prompts.py --disable=all --enable=C0302 --max-module-lines=200` — passes
- [ ] `uvx pylint nl_processing/core/scripts/prompt_author.py --disable=all --enable=C0302 --max-module-lines=200` — passes

## Edge cases

- The `load()` function emits a `LangChainBetaWarning`. This is expected and does not affect functionality. Tests may see this warning in output — that's fine.
- `load()` with an empty dict `{}` should raise an exception (no `"lc"` key) — tests should cover this.
- A JSON file containing a valid LangChain serialization of something other than `ChatPromptTemplate` (e.g., a `PromptTemplate`) should raise `TypeError` — the new type check handles this.

## Notes / risks

- **Risk**: Other modules might also have prompt JSON files in the old format.
  - **Mitigation**: Verified — only `extract_text_from_image` has a prompt JSON file (`nl_processing/extract_text_from_image/prompts/nl.json`). No other module has created prompt files yet. The cross-module concern is a non-issue for this sprint. As a final sanity check, run `uv run pytest tests/unit/ -x -v` after this task to confirm no other module is affected.
