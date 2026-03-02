---
Task ID: `T5`
Title: `Implement prompt loading utility with unit tests`
Sprint: `2026-03-02_module-core`
Module: `core`
Depends on: `T2`
Parallelizable: `yes, with T3, T4`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Create `nl_processing/core/prompts.py` with a `load_prompt()` utility function that loads a LangChain `ChatPromptTemplate` from a JSON file in ChatPromptTemplate native serialization format. After this task, any module can load its language-specific prompt JSON files using this utility without custom parsing.

## Context (contract mapping)

- Requirements: `docs/planning-artifacts/prd.md` — CFR10 (prompt loading utility), CFR13 (ChatPromptTemplate native format), CFR14 (core provides loading only, not content)
- Architecture: `docs/planning-artifacts/architecture.md` — "Prompt JSON Format — LangChain ChatPromptTemplate Serialization", "Prompt File Organization", core interface `load_prompt(prompt_path: str) -> ChatPromptTemplate`
- Epics: `docs/planning-artifacts/epics.md` — Story 1.3: Core Prompt Loading Utility

## Preconditions

- T2 completed — `langchain>=0.3,<1` is installed, `ChatPromptTemplate` is importable
- `nl_processing/core/__init__.py` exists (may be created by T3/T4 running in parallel; if not, create it here — empty)

## Non-goals

- No prompt content creation — that is each module's responsibility
- No prompt authoring helper (that is T6)
- No runtime chain construction — only loading the prompt template from JSON

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/core/__init__.py` (create if not exists, must be empty)
- `nl_processing/core/prompts.py` (create)
- `tests/unit/core/__init__.py` (create if not exists, must be empty)
- `tests/unit/core/test_prompts.py` (create)

**FORBIDDEN — this task must NEVER touch:**
- Any other module's code or tests
- `nl_processing/core/models.py` (T3)
- `nl_processing/core/exceptions.py` (T4)
- `pyproject.toml`
- Any docs outside `docs/sprints/module-core/`

**Test scope:**
- Tests go in: `tests/unit/core/test_prompts.py`
- Test command: `uv run pytest tests/unit/core/test_prompts.py -x -v`

## Touched surface (expected files / modules)

- `nl_processing/core/__init__.py` — created if not exists, empty
- `nl_processing/core/prompts.py` — created
- `tests/unit/core/__init__.py` — created if not exists, empty
- `tests/unit/core/test_prompts.py` — created

## Dependencies and sequencing notes

- Depends on T2 (LangChain installed)
- Can run in parallel with T3 (models) and T4 (exceptions) — no file overlap
- T6 (prompt authoring helper) depends on this task because the helper serializes prompts that must be loadable by `load_prompt()`
- T7 depends on this task

## Third-party / library research (mandatory for any external dependency)

- **Library**: `langchain-core` (installed as dependency of `langchain>=0.3,<1`)
  - **Official documentation**: https://python.langchain.com/docs/concepts/prompt_templates/
  - **API reference — ChatPromptTemplate**: https://python.langchain.com/api_reference/core/prompts/langchain_core.prompts.chat.ChatPromptTemplate.html
  - **Serialization/deserialization**:
    - **Save to JSON**: `prompt.save("path.json")` — saves as JSON using LangChain's native serialization.
    - **Load from JSON**: `langchain_core.load.load(json_data)` or `langchain_core.prompts.load_prompt("path.json")` — loads from the serialized JSON.
    - **Alternative load**: `langchain_core.load.loads(json_string)` for loading from a string.
  - **Verified usage pattern**:
    ```python
    from langchain_core.prompts import ChatPromptTemplate

    # Create and save
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant."),
        ("human", "{input}"),
    ])
    prompt.save("prompt.json")

    # Load
    from langchain_core.prompts import load_prompt
    loaded = load_prompt("prompt.json")
    ```
  - **Known gotchas**:
    - `load_prompt` from `langchain_core.prompts` is the canonical loader. It returns the prompt template directly.
    - The JSON format includes `type`, `messages`, and metadata — it is LangChain's internal format, not a custom one.
    - `load_prompt` expects a file path (string or Path), not a JSON dict. It reads the file internally.
    - If the JSON file is malformed or missing required fields, it raises a `ValueError` or JSON decode error.
    - The `allow_dangerous_deserialization` parameter may be required for loading prompts with certain types. For `ChatPromptTemplate`, it is typically not needed.

## Implementation steps (developer-facing)

1. **Ensure `nl_processing/core/` directory exists**.
2. **Ensure `nl_processing/core/__init__.py`** exists and is empty.
3. **Create `nl_processing/core/prompts.py`** with:
   ```python
   from langchain_core.prompts import ChatPromptTemplate
   from langchain_core.prompts import load_prompt as _langchain_load_prompt


   def load_prompt(prompt_path: str) -> ChatPromptTemplate:
       """Load a ChatPromptTemplate from a JSON file.

       Args:
           prompt_path: Path to the prompt JSON file in LangChain ChatPromptTemplate
                        native serialization format.

       Returns:
           A ChatPromptTemplate ready for chain composition.

       Raises:
           FileNotFoundError: If the prompt file does not exist.
           ValueError: If the JSON file is malformed.
       """
       result = _langchain_load_prompt(prompt_path)
       if not isinstance(result, ChatPromptTemplate):
           msg = f"Expected ChatPromptTemplate, got {type(result).__name__}"
           raise TypeError(msg)
       return result
   ```
   **Notes:**
   - Wraps LangChain's `load_prompt` for type safety — ensures the return type is `ChatPromptTemplate`.
   - Delegates file reading and JSON parsing to LangChain — no custom parsing.
   - `FileNotFoundError` propagates naturally from LangChain's file reading.
   - Type hint on return value ensures callers know they get `ChatPromptTemplate`.

4. **Ensure `tests/unit/core/` directory exists**.
5. **Ensure `tests/unit/core/__init__.py`** exists and is empty.
6. **Create `tests/unit/core/test_prompts.py`** with tests covering:
   - **Valid prompt loading**: Create a temporary JSON file with a valid ChatPromptTemplate serialization (using `ChatPromptTemplate.from_messages([...]).save(tmp_path)`), then load it with `load_prompt()` and verify the result is a `ChatPromptTemplate`.
   - **Missing file**: Call `load_prompt("nonexistent.json")` — verify `FileNotFoundError` is raised.
   - **Malformed JSON**: Create a temp file with invalid JSON content, call `load_prompt()` — verify an error is raised.
   - **Round-trip**: Create a prompt, save it, load it, verify the loaded prompt has the same messages as the original.
   - Use `pytest`'s `tmp_path` fixture for temporary file creation — no cleanup needed.

7. **Run tests**: `uv run pytest tests/unit/core/test_prompts.py -x -v`
8. **Run linting**: `uv run ruff format nl_processing/core/prompts.py tests/unit/core/test_prompts.py && uv run ruff check nl_processing/core/prompts.py tests/unit/core/test_prompts.py`

## Production safety constraints (mandatory)

- **Database operations**: None.
- **Resource isolation**: Tests use `tmp_path` fixture — no shared file paths. No production file access.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Wraps LangChain's existing `load_prompt` — does not reinvent JSON parsing.
- **Correct libraries only**: `langchain-core` from `langchain>=0.3,<1` in `pyproject.toml`.
- **Correct file locations**: `nl_processing/core/prompts.py` per architecture spec.
- **No regressions**: New files — no existing functionality affected.

## Error handling + correctness rules (mandatory)

- Do not catch/silence `FileNotFoundError` — let it propagate to the caller.
- Do not catch/silence JSON parsing errors — let them propagate.
- The `TypeError` for non-`ChatPromptTemplate` return is an explicit correctness check — fail fast.

## Zero legacy tolerance rule (mandatory)

- No legacy to remove — these are new files.
- Ensure no `__init__.py` re-exports.

## Acceptance criteria (testable)

1. `from nl_processing.core.prompts import load_prompt` succeeds
2. `load_prompt(valid_json_path)` returns a `ChatPromptTemplate` instance
3. Round-trip: save a `ChatPromptTemplate`, load it, verify messages match
4. `load_prompt("nonexistent.json")` raises `FileNotFoundError`
5. `load_prompt(malformed_json_path)` raises an error (not silenced)
6. `uv run pytest tests/unit/core/test_prompts.py -x -v` passes
7. `uv run ruff check nl_processing/core/prompts.py tests/unit/core/test_prompts.py` passes
8. `nl_processing/core/prompts.py` is under 200 lines

## Verification / quality gates

- [ ] Unit tests added in `tests/unit/core/test_prompts.py`
- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] Negative-path tests exist (missing file, malformed JSON)

## Edge cases

- Prompt JSON file with empty messages list — LangChain may accept this; test if needed.
- Very large prompt file — not a concern for this project (prompts are small).
- If `langchain_core.prompts.load_prompt` signature differs from researched version, adapt the wrapper. Verify by running the unit tests.

## Rollout / rollback (if relevant)

- Rollout: Create files in a single commit.
- Rollback: Delete the created files.

## Notes / risks

- **Risk**: LangChain `load_prompt` API may differ between `langchain-core` versions. **Mitigation**: Unit tests verify the exact behavior. The version range `>=0.3,<1` is pinned. If the API is different, adapt the wrapper function and update tests.
- **Risk**: `load_prompt` may require `allow_dangerous_deserialization=True` for certain prompt types. **Mitigation**: For `ChatPromptTemplate` (the only type we use), this is typically not required. If needed, add the parameter explicitly and document why.
