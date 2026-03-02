---
Task ID: `T6`
Title: `Implement prompt authoring helper script`
Sprint: `2026-03-02_module-core`
Module: `core`
Depends on: `T5`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Create `nl_processing/core/scripts/prompt_author.py` — a standalone dev-time script that serializes inline Python prompt definitions (using LangChain `ChatPromptTemplate`) to JSON files. After this task, module developers can author prompts in Python and export them to the JSON format expected by `load_prompt()` from T5.

## Context (contract mapping)

- Requirements: `docs/planning-artifacts/prd.md` — CFR12 (prompt authoring helper script in `core/scripts/`), CFR13 (ChatPromptTemplate native format)
- Architecture: `docs/planning-artifacts/architecture.md` — "Core Package Structure (Flat)" shows `scripts/prompt_author.py`, "`scripts/` is not a Python package — it contains standalone dev tools"
- Epics: `docs/planning-artifacts/epics.md` — Story 1.4: Prompt Authoring Helper Script

## Preconditions

- T5 completed — `load_prompt()` works, so we can verify round-trip: author → save → load
- LangChain is installed (T2)

## Non-goals

- No prompt content authoring — the script provides the mechanism, not the content
- No CLI argument parsing — the script is a helper template, not a polished CLI tool
- No `__init__.py` in `scripts/` — it is NOT a Python package
- No unit tests for the script in `tests/unit/core/` — the script is a dev tool verified by running it manually and loading the output with `load_prompt()`

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/core/scripts/prompt_author.py` (create)
- `nl_processing/core/scripts/` directory (create — no `__init__.py`)

**FORBIDDEN — this task must NEVER touch:**
- Any other module's code or tests
- `nl_processing/core/__init__.py`, `models.py`, `exceptions.py`, `prompts.py`
- `tests/` (no new test files for this task)
- `pyproject.toml`
- Any docs outside `docs/sprints/module-core/`

**Test scope:**
- No automated tests for this task — the script is a dev tool
- Verification: manually run the script and verify the output JSON loads via `load_prompt()`

## Touched surface (expected files / modules)

- `nl_processing/core/scripts/` directory — created
- `nl_processing/core/scripts/prompt_author.py` — created

## Dependencies and sequencing notes

- Depends on T5 because the script's output must be loadable by `load_prompt()`
- Not parallelizable — sequential after T5
- T7 depends on this task (final verification)

## Third-party / library research (mandatory for any external dependency)

- **Library**: `langchain-core` (already researched in T5)
  - **Save API**: `ChatPromptTemplate.save(file_path)` — serializes to JSON
  - **Verified pattern**:
    ```python
    from langchain_core.prompts import ChatPromptTemplate

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a {role}. Respond in {language}."),
        ("human", "{input}"),
    ])
    prompt.save("output.json")
    ```
  - The saved JSON file uses LangChain's internal serialization format and can be loaded by `load_prompt()` from T5.

## Implementation steps (developer-facing)

1. **Create `nl_processing/core/scripts/` directory**. Do NOT create an `__init__.py` — this is not a Python package.
2. **Create `nl_processing/core/scripts/prompt_author.py`** as a standalone script:
   ```python
   """Prompt authoring helper — serialize ChatPromptTemplate to JSON.

   Usage:
       1. Edit the `build_prompt()` function below to define your prompt.
       2. Set OUTPUT_PATH to your desired output file path.
       3. Run: uv run python nl_processing/core/scripts/prompt_author.py

   The output JSON can be loaded by `nl_processing.core.prompts.load_prompt()`.
   """

   from langchain_core.prompts import ChatPromptTemplate


   def build_prompt() -> ChatPromptTemplate:
       """Define your prompt here. Edit this function for each prompt you author."""
       return ChatPromptTemplate.from_messages([
           ("system", "You are a helpful assistant. Respond in {language}."),
           ("human", "{input}"),
       ])


   OUTPUT_PATH = "output_prompt.json"


   if __name__ == "__main__":
       prompt = build_prompt()
       prompt.save(OUTPUT_PATH)
       print(f"Prompt saved to {OUTPUT_PATH}")  # noqa: T201 — dev script, print is intentional
   ```
   **Notes:**
   - The `print` statement is intentional for a dev script. The `ruff.toml` already has `scripts/*` in `per-file-ignores` for T201. However, this file is at `nl_processing/core/scripts/`, not `scripts/`. Add a `noqa: T201` inline comment to suppress the print ban for this dev script.
   - The developer modifies `build_prompt()` and `OUTPUT_PATH` for each prompt they want to author.
   - The script is self-contained — no imports from other `core` modules.

3. **Verify manually**:
   ```bash
   uv run python nl_processing/core/scripts/prompt_author.py
   # Check output_prompt.json exists and contains valid JSON
   uv run python -c "from nl_processing.core.prompts import load_prompt; p = load_prompt('output_prompt.json'); print(type(p))"
   # Clean up
   rm output_prompt.json
   ```

4. **Run linting**: `uv run ruff format nl_processing/core/scripts/prompt_author.py && uv run ruff check nl_processing/core/scripts/prompt_author.py`

## Production safety constraints (mandatory)

- **Database operations**: None.
- **Resource isolation**: The script writes to a local file (specified by `OUTPUT_PATH`). No production file paths involved.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Uses LangChain's built-in `.save()` method — no custom serialization.
- **Correct libraries only**: `langchain-core` from `langchain>=0.3,<1`.
- **Correct file locations**: `nl_processing/core/scripts/prompt_author.py` per architecture spec.
- **No regressions**: New file — no existing functionality affected.

## Error handling + correctness rules (mandatory)

- If `build_prompt()` raises an error, it propagates — no silencing.
- If `.save()` fails (e.g., invalid path), it propagates — no silencing.

## Zero legacy tolerance rule (mandatory)

- No legacy to remove — new file.
- `scripts/` directory must NOT contain an `__init__.py`.

## Acceptance criteria (testable)

1. `nl_processing/core/scripts/prompt_author.py` exists
2. `nl_processing/core/scripts/__init__.py` does NOT exist
3. Running `uv run python nl_processing/core/scripts/prompt_author.py` produces a JSON file
4. The JSON file can be loaded by `load_prompt()` from `nl_processing.core.prompts` and returns a `ChatPromptTemplate`
5. `uv run ruff check nl_processing/core/scripts/prompt_author.py` passes (no errors)
6. File is under 200 lines

## Verification / quality gates

- [x] Linters/formatters pass
- [x] No new warnings introduced
- [x] Manual verification: script runs, output loads successfully

## Edge cases

- If the `T201` (print ban) ruff rule is not suppressed via `per-file-ignores` for this path, the `noqa: T201` inline comment handles it.
- If `vulture` flags `build_prompt` or `OUTPUT_PATH` as unused, add them to `vulture_whitelist.py` in T7.

## Rollout / rollback (if relevant)

- Rollout: Create the script file.
- Rollback: Delete the file and the `scripts/` directory.

## Notes / risks

- **Risk**: `vulture` may flag functions/variables in the script as unused. **Mitigation**: Handle in T7 (vulture whitelist update if needed).
- **Risk**: `ruff` per-file-ignores for `scripts/*` in `ruff.toml` matches `scripts/` at repo root, not `nl_processing/core/scripts/`. The `noqa` inline comment handles this. Alternatively, the developer may add `"nl_processing/core/scripts/*"` to `per-file-ignores` — but modifying `ruff.toml` is out of scope for this sprint. Use `noqa` instead.
