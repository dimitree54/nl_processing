# Task: Consolidate image and AI prompt helpers into `core`

## Status

- Ready for implementation after documentation alignment is completed first.

## Why this task exists

`packages/extract_text_from_image` currently owns prompt-generation helpers that are really shared low-level infrastructure:

- synthetic test-image generation lives in `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/prompts/_synthetic_image.py`
- synthetic-image data URL generation lives as private `_generate_image_b64(...)` in `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/prompts/generate_nl_prompt.py`
- example AI tool-call message creation lives as private `_make_example_ai(...)` in `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/prompts/generate_nl_prompt.py`
- the service re-wraps missing-file errors into package-local `ImageTextFileNotFoundError`

The requested change is to move the reusable helpers into `packages/core`, make the new helpers part of the documented public contract there, reuse them from `extract_text_from_image`, and stop exposing a package-specific missing-file exception.

## Blocking documentation contradiction

This repo is documentation-driven. Implementation must not start until the module specs are updated to match the target contract.

Current contradiction to resolve first:

- `packages/extract_text_from_image/docs/module-spec.md` currently documents `ImageTextFileNotFoundError` as public behavior for missing files.
- `packages/core/docs/module-spec.md` currently documents image validation, path/cv2 encoding, and human-image message helpers, but does not yet document the requested public synthetic-image generator or shared AI-message helper.

Implementation order must therefore begin with spec updates in both packages before any source refactor.

## Relevant skills to read

- `feature-request` - use the repo's feature-delivery/TDD workflow.
- `module-spec-agent` - use when updating the module specs so the public contract changes are explicit and complete.

## Repo and module context reviewed

- Repo overview: `README.md`
- Core spec: `packages/core/docs/module-spec.md`
- Extract-text-from-image spec: `packages/extract_text_from_image/docs/module-spec.md`
- Core image helpers: `packages/core/src/nl_processing/core/image_encoding.py`
- Core prompt helpers: `packages/core/src/nl_processing/core/prompts.py`
- Extractor service: `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/service.py`
- Prompt generator: `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/prompts/generate_nl_prompt.py`
- Current synthetic image helper: `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/prompts/_synthetic_image.py`
- Package-local exception to remove: `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/exceptions.py`
- Current core image-helper tests: `packages/core/tests/unit/core/test_image_encoding.py`
- Current extract-text-from-image tests using synthetic-image helper and file-missing behavior:
  - `packages/extract_text_from_image/tests/unit/extract_text_from_image/test_error_handling.py`
  - `packages/extract_text_from_image/tests/unit/extract_text_from_image/test_extract_text_from_image.py`
  - `packages/extract_text_from_image/tests/unit/extract_text_from_image/test_image_encoding.py`
  - `packages/extract_text_from_image/tests/e2e/extract_text_from_image/test_extraction_accuracy.py`

## Cross-module impact

### `packages/core`

This package becomes the owner of new public reusable helpers for:

- synthetic test-image generation
- synthetic-image data URL generation for few-shot prompts
- shared AI tool-call message creation for prompt examples

Expected files to change:

- `packages/core/docs/module-spec.md`
- `packages/core/src/nl_processing/core/image_encoding.py`
- `packages/core/src/nl_processing/core/prompts.py`
- `packages/core/tests/unit/core/test_image_encoding.py`
- `packages/core/tests/unit/core/test_prompts.py`

### `packages/extract_text_from_image`

This package stops owning duplicate low-level helpers and stops translating missing-file failures into a module-local exception.

Expected files to change:

- `packages/extract_text_from_image/docs/module-spec.md`
- `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/service.py`
- `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/prompts/generate_nl_prompt.py`
- `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/prompts/_synthetic_image.py`
- `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/exceptions.py`
- `packages/extract_text_from_image/tests/unit/extract_text_from_image/test_error_handling.py`
- `packages/extract_text_from_image/tests/unit/extract_text_from_image/test_extract_text_from_image.py`
- `packages/extract_text_from_image/tests/unit/extract_text_from_image/test_image_encoding.py`
- `packages/extract_text_from_image/tests/e2e/extract_text_from_image/test_extraction_accuracy.py`

## Target design decisions

These choices are already made for the implementer; do not re-decide them during implementation.

1. Keep image-related helpers in `packages/core/src/nl_processing/core/image_encoding.py`.
2. Keep message-construction helpers in `packages/core/src/nl_processing/core/prompts.py`.
3. Promote `generate_test_image(...)` into `core.image_encoding` as a public helper with the same observable behavior and parameters currently used by tests.
4. Replace private `_generate_image_b64(...)` with public `generate_test_image_data_url(text: str, *, width: int = 800, height: int = 200, font_scale: float = 1.2, thickness: int = 2) -> str` in `nl_processing.core.image_encoding`.
5. Replace private `_make_example_ai(...)` with public `build_tool_call_ai_message(tool_name: str, tool_args: dict[str, object], call_id: str, *, content: str = "") -> AIMessage` in `nl_processing.core.prompts`.
6. `generate_nl_prompt.py` must remove `_make_example_human(...)` and build human image messages by parsing each generated or existing data URL once into `(base64_string, media_type)`, then passing those values to `build_image_human_message(base64_string, media_type)`. Do not add a second core helper for data-URL-to-human-message conversion.
7. `ImageTextExtractor.extract_from_path(...)` must allow native `FileNotFoundError` from `encode_image_path(...)` to propagate; do not catch and re-raise a package-specific exception.
8. Remove `ImageTextFileNotFoundError` from the package source and tests once no code depends on it.

## Implementation plan

### 1. Align public docs first

Update `packages/core/docs/module-spec.md` to explicitly add the new public contract items:

- public synthetic test-image generator
- public `generate_test_image_data_url(text: str, *, width: int = 800, height: int = 200, font_scale: float = 1.2, thickness: int = 2) -> str`
- public `build_tool_call_ai_message(tool_name: str, tool_args: dict[str, object], call_id: str, *, content: str = "") -> AIMessage`
- any new failure semantics these helpers expose, including native `FileNotFoundError` and `ValueError` behavior where applicable

Update `packages/extract_text_from_image/docs/module-spec.md` to remove `ImageTextFileNotFoundError` from all public contract sections and replace missing-path behavior with native `FileNotFoundError` propagation.

Also update the spec language that describes shared `core` helper ownership so it now includes the new public helpers consumed by prompt generation.

### 2. Move image helper ownership into `core`

In `packages/core/src/nl_processing/core/image_encoding.py`:

- move the logic from `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/prompts/_synthetic_image.py` into a public `generate_test_image(...)`
- add public `generate_test_image_data_url(text: str, *, width: int = 800, height: int = 200, font_scale: float = 1.2, thickness: int = 2) -> str`
- implement `generate_test_image_data_url(...)` by generating a temp PNG with `generate_test_image(...)`, encoding it with existing `encode_path_to_base64(...)`, and returning `data:{media_type};base64,{base64_string}`
- implement the data URL helper by composing existing core helpers rather than duplicating base64 or media-type logic
- keep temp-file lifecycle internal to the helper

Then remove the now-redundant package-local implementation in `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/prompts/_synthetic_image.py`.

### 3. Add shared AI-message helper in `core`

In `packages/core/src/nl_processing/core/prompts.py` add public `build_tool_call_ai_message(tool_name: str, tool_args: dict[str, object], call_id: str, *, content: str = "") -> AIMessage`.

Required behavior:

- returns `langchain_core.messages.AIMessage`
- preserves empty-string `content` by default
- writes exactly one tool call using caller-supplied `tool_name`, `tool_args`, and `call_id`
- does not bake in `ExtractedText` or any package-specific schema name

Required call shape:

```python
message = build_tool_call_ai_message("ExtractedText", {"text": expected_text}, "call_example_1")
```

### 4. Refactor `generate_nl_prompt.py` to consume `core`

In `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/prompts/generate_nl_prompt.py`:

- stop importing `generate_test_image` from package-local `_synthetic_image.py`
- import the new public synthetic-image helpers from `nl_processing.core.image_encoding`
- import the new AI-message helper from `nl_processing.core.prompts`
- remove `_generate_image_b64(...)`
- remove `_make_example_ai(...)`
- remove `_make_example_human(...)`
- keep `_encode_existing_image_b64(...)` as a local helper for bundled example JPG files; do not introduce a new core helper for existing-file data URLs in this task
- add one small local helper that parses a full data URL into `(base64_string, media_type)` and immediately passes those values to `build_image_human_message(...)`
- use that local parser/helper for both generated data URLs from `generate_test_image_data_url(...)` and existing-file data URLs returned by `_encode_existing_image_b64(...)`

The prompt content and example ordering must not change.

### 5. Remove package-specific missing-file exception behavior

In `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/service.py`:

- delete the `try/except FileNotFoundError` wrapper around `encode_image_path(path)`
- update docstrings to state `FileNotFoundError` instead of `ImageTextFileNotFoundError`

Then remove the now-unused package exception module:

- delete `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/exceptions.py`

If any imports remain, remove them rather than leaving dead compatibility shims.

### 6. Update tests to the new contract

In `packages/core/tests/unit/core/test_image_encoding.py` add coverage for:

- `generate_test_image(...)` writes an image file successfully
- the synthetic-image data URL helper returns a `data:image/png;base64,...` URL
- generated data URL decodes to non-empty image bytes

In `packages/core/tests/unit/core/test_prompts.py` add coverage for the new AI-message helper:

- message type is `AIMessage`
- `content` defaults to `""`
- exactly one tool call is emitted with the provided `name`, `args`, and `id`

In `packages/extract_text_from_image` tests:

- replace imports of package-local `generate_test_image` with the new public `core.image_encoding.generate_test_image`
- change missing-file expectations from `ImageTextFileNotFoundError` to native `FileNotFoundError`
- keep existing success/error semantics for unsupported format, blank extraction, and API wrapping unchanged

## API and library usage notes

### Existing repo usage to follow

- `packages/core/src/nl_processing/core/image_encoding.py` already defines the canonical human image-message shape through `build_image_human_message(base64_string, media_type)`.
- `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/prompts/generate_nl_prompt.py` already shows the current AI tool-call payload structure that must be preserved when moving to `core`.

Current AI tool-call shape to preserve:

```python
AIMessage(
    content="",
    tool_calls=[{"name": "ExtractedText", "args": {"text": expected_text}, "id": call_id}],
)
```

Current human image-message shape already validated in core tests:

```python
HumanMessage(
    content=[
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}},
    ]
)
```

Required local refactor path in `generate_nl_prompt.py`:

```python
img1 = generate_test_image_data_url(EXAMPLE_1_TEXT)
human1 = _build_human_message_from_data_url(img1)
```

Where `_build_human_message_from_data_url(...)` is a local helper that:

1. strips the `data:` prefix
2. splits once on `";base64,"`
3. passes the parsed `media_type` and `base64_string` into `build_image_human_message(...)`

This keeps `build_image_human_message(...)` as the only human-message constructor while avoiding any ambiguous decompose/recompose logic.

### External references

- LangChain message concepts: `https://python.langchain.com/docs/concepts/messages/`
- LangChain Core reference index for `AIMessage` and `HumanMessage`: `https://reference.langchain.com/python/langchain-core/`

Use these only to confirm message object expectations; implementation should primarily follow the existing repo patterns already in use.

## Dependencies

### Code dependencies

- `packages/extract_text_from_image` depends on `packages/core` via local path dependency declared in `packages/extract_text_from_image/pyproject.toml`.
- `packages/core` already depends on `langchain-core`, `langchain-openai`, `numpy`, and `opencv-python`, so the requested helper moves do not require new package dependencies.

### Task ordering dependencies

1. Update both module specs.
2. Add new public helpers in `core` with tests.
3. Refactor `extract_text_from_image` to consume the new helpers.
4. Remove the package-local exception and synthetic helper module.
5. Run full quality gates in both affected packages.

## Risks

- Public-contract expansion in `core` means the new public names `generate_test_image_data_url(...)` and `build_tool_call_ai_message(...)` must remain stable once released.
- Removing `ImageTextFileNotFoundError` changes caller-facing exception typing in `extract_text_from_image`; all tests and docs must move in lockstep.
- `generate_nl_prompt.py` is already close to the repo file-size limit at 199 lines; the refactor must reduce or maintain size, not push it over the 200-line lint gate.
- Deleting `_synthetic_image.py` can break tests or prompt tooling if any remaining imports are missed.

## Acceptance criteria

- `packages/core/docs/module-spec.md` documents public `generate_test_image(...)`, `generate_test_image_data_url(...)`, and `build_tool_call_ai_message(...)` with their exact signatures.
- `packages/extract_text_from_image/docs/module-spec.md` no longer documents `ImageTextFileNotFoundError` and instead documents native `FileNotFoundError` for missing image paths.
- `nl_processing.core.image_encoding` exposes public `generate_test_image(...)` and `generate_test_image_data_url(...)`, and both are covered by unit tests.
- `nl_processing.core.prompts` exposes public `build_tool_call_ai_message(...)` and it is covered by unit tests.
- `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/prompts/generate_nl_prompt.py` uses `build_image_human_message(...)` and the new `core` helpers instead of package-local helper implementations.
- `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/service.py` no longer imports or raises `ImageTextFileNotFoundError`.
- `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/exceptions.py` is removed.
- All updated tests assert the new missing-file behavior with `FileNotFoundError` and continue to verify unchanged behavior elsewhere.
- `make check` passes in both `packages/core` and `packages/extract_text_from_image` with no new lint, duplication, or file-size regressions.

## Quality gates

Run all of the following and require green results:

### `packages/core`

- `make check`
- minimum expected coverage within that gate:
  - `uv run pytest -n auto tests/unit`
  - Ruff format/check
  - Pylint max-module-lines gate
  - Vulture
  - JSCPD

### `packages/extract_text_from_image`

- `make check`
- minimum expected coverage within that gate:
  - `uv run pytest -n auto tests/unit`
  - `doppler run -- uv run pytest -n auto tests/e2e`
  - Ruff format/check
  - Pylint max-module-lines gate
  - Vulture
  - JSCPD

## Done definition

- Docs and source agree on the new public contract before the task is considered complete.
- No package-local duplicate helper remains for the moved responsibilities.
- No package-local missing-file exception remains in `extract_text_from_image`.
- Both affected packages are fully green on their package-local `make check` commands.
