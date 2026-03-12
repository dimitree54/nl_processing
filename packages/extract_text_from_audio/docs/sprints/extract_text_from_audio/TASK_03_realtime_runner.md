---
Task ID: `T3`
Title: `Create realtime audio runner in core`
Sprint: `2026-03-12_extract-text-from-audio`
Module: `extract_text_from_audio`
Depends on: `T1`
Parallelizable: `yes, with T2`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Create a shared `core.realtime_runner` module that opens a short-lived WebSocket session to the OpenAI Realtime API (`gpt-realtime-mini`), submits base64-encoded audio as a single conversation turn, and returns the text-only final response. This is the new shared infrastructure required by IF-3 / DEC-1 from the module spec — it does NOT use LangChain.

## Context (contract mapping)

- Requirements: `packages/extract_text_from_audio/docs/module-spec.md` — IF-3 (realtime runner), IF-4 (gpt-realtime-mini session), DEC-1 (new shared realtime infrastructure), FR-9 (APIError wrapping)
- Architecture: DEC-2 (gpt-realtime-mini directly), BR-1 (no model swap)
- Reference: OpenAI Realtime API WebSocket guide — `wss://api.openai.com/v1/realtime?model=gpt-realtime-mini`

## Preconditions

- T1 completed: `UnsupportedAudioFormatError` and root config updates exist.
- `make check` passes from `packages/extract_text_from_audio/`.

## Non-goals

- Audio output / voice response (text-only output)
- Streaming to the caller (batch one-shot request-response)
- WebRTC connection (server-side only, WebSocket is correct)
- Function calling / tool use within the realtime session
- Retry logic (caller handles retries if needed)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `packages/core/src/nl_processing/core/realtime_runner.py` — new file
- `packages/extract_text_from_audio/tests/unit/extract_text_from_audio/test_realtime_runner.py` — new unit tests

**FORBIDDEN — this task must NEVER touch:**
- Any other module's code or tests
- `core/prompts.py`, `core/image_encoding.py`, `core/exceptions.py`
- Bot code

**Test scope:**
- Tests go in: `packages/extract_text_from_audio/tests/unit/extract_text_from_audio/`
- Test command: `make check` from `packages/extract_text_from_audio/`

## Touched surface (expected files / modules)

- `packages/core/src/nl_processing/core/realtime_runner.py` (new)
- `packages/extract_text_from_audio/tests/unit/extract_text_from_audio/test_realtime_runner.py` (new)

## Dependencies and sequencing notes

- Depends on T1 (core exception available, make check works).
- Can run in parallel with T2 (WAV validator) — no file overlap.
- T4 (service) depends on this task.

## Third-party / library research (mandatory for any external dependency)

### `websockets` library
- **Library**: `websockets` — modern async WebSocket client/server library for Python
- **Version**: Latest stable is `14.2` (as of March 2026). Use `>=14.0,<15`.
- **Official documentation**: https://websockets.readthedocs.io/en/stable/
- **API reference (client)**: https://websockets.readthedocs.io/en/stable/reference/asyncio/client.html
- **Usage pattern (async context manager)**:
  ```python
  import websockets

  async with websockets.connect(uri, additional_headers=headers) as ws:
      await ws.send(json.dumps(event))
      async for message in ws:
          data = json.loads(message)
          # process server events
  ```
- **Known gotchas**:
  - `websockets.connect()` returns an async context manager. The connection is closed when the context exits.
  - The `additional_headers` parameter accepts a dict or list of tuples for custom headers (used for Authorization).
  - The library raises `websockets.exceptions.ConnectionClosed` on unexpected disconnects.
  - In v14+, `websockets.connect` is the primary API (legacy `websockets.client.connect` still works but prefer the modern one).
- **Rate limits**: OpenAI Realtime API has rate limits per model. `gpt-realtime-mini` limits are documented at https://platform.openai.com/docs/guides/rate-limits. For short-lived single-turn sessions, rate limits are unlikely to be hit in tests.

### OpenAI Realtime API (WebSocket protocol)
- **WebSocket URL**: `wss://api.openai.com/v1/realtime?model=gpt-realtime-mini`
- **Authentication**: `Authorization: Bearer <OPENAI_API_KEY>` header
- **Session lifecycle** (GA interface):
  1. Connect to WebSocket. Server sends `session.created` event.
  2. Send `session.update` to configure the session (type, instructions, modalities, input audio format).
  3. Send `conversation.item.create` with a user message containing `input_audio` (base64-encoded PCM or WAV).
  4. Send `response.create` to trigger the model response.
  5. Receive `response.output_text.delta` events with text chunks.
  6. Receive `response.done` event with the complete response.
  7. Close the WebSocket.
- **Key event types** (GA interface):
  - Client sends: `session.update`, `conversation.item.create`, `response.create`
  - Server sends: `session.created`, `session.updated`, `conversation.item.added`, `response.output_text.delta`, `response.output_text.done`, `response.done`, `error`
- **Audio format**: The Realtime API accepts base64-encoded PCM 16-bit 24kHz mono by default. WAV files need to be read and their raw PCM data extracted and base64-encoded, or the entire WAV can be sent if the session's input audio format is configured for it.
- **Text-only output**: Set session modalities to `["text"]` to receive text-only responses (no audio output).
- **Documentation**: https://platform.openai.com/docs/guides/realtime-websocket, https://platform.openai.com/docs/guides/realtime-conversations

### `pyproject.toml` dependency
- The `websockets` library must be added to `packages/core/pyproject.toml` as a dependency. Check the existing core `pyproject.toml` for the correct format.

## Implementation steps (developer-facing)

1. **Add `websockets` dependency** to `packages/core/pyproject.toml`:
   ```toml
   dependencies = [
     ...,
     "websockets>=14.0,<15",
   ]
   ```

2. **Create `packages/core/src/nl_processing/core/realtime_runner.py`** with the following structure:

   ```python
   """Shared realtime audio runner — opens a short-lived gpt-realtime-mini WebSocket session."""

   import base64
   import json
   import os

   import websockets

   from nl_processing.core.exceptions import APIError

   _REALTIME_URL = "wss://api.openai.com/v1/realtime"


   async def run_realtime_audio_session(
       *,
       audio_bytes: bytes,
       instructions: str,
       model: str = "gpt-realtime-mini",
   ) -> str:
       """Submit audio to a short-lived Realtime session and return text transcript.

       Opens a WebSocket, configures a text-only session with the given instructions,
       sends the audio as a single conversation turn, and collects the full text response.

       Args:
           audio_bytes: Raw WAV file bytes.
           instructions: System-level instructions for the session.
           model: Realtime model identifier.

       Returns:
           The plain text response from the model.

       Raises:
           APIError: On connection, protocol, or response parsing failures.
       """
   ```

   The function should:
   a. Read `OPENAI_API_KEY` from `os.environ["OPENAI_API_KEY"]` (fail-fast, no fallback).
   b. Base64-encode the audio bytes.
   c. Connect via `websockets.connect(f"{_REALTIME_URL}?model={model}", additional_headers={"Authorization": f"Bearer {api_key}"})`.
   d. Wait for the `session.created` server event.
   e. Send `session.update` with `type: "realtime"`, `modalities: ["text"]`, and `instructions`.
   f. Send `conversation.item.create` with a user message containing `input_audio` content (base64-encoded audio).
   g. Send `response.create` to trigger the response.
   h. Collect `response.output_text.delta` events, concatenating their `delta` fields.
   i. On `response.done`, return the concatenated text.
   j. On `error` events, raise `APIError` with the error message.
   k. Wrap all `websockets` exceptions, `json.JSONDecodeError`, `KeyError`, and unexpected protocol errors in `APIError` with chained cause.

3. **File size**: Keep `realtime_runner.py` well under 200 lines. If it approaches the limit, extract helper functions (e.g., `_build_session_update_event`, `_build_audio_item_event`) into clear private functions within the same file, or decompose into a sub-module.

4. **Create unit tests** in `packages/extract_text_from_audio/tests/unit/extract_text_from_audio/test_realtime_runner.py`:
   - `test_run_realtime_missing_api_key` — unset `OPENAI_API_KEY`, verify `KeyError` is raised (fail-fast, no fallback).
   - `test_realtime_url_constant` — verify `_REALTIME_URL` is `"wss://api.openai.com/v1/realtime"`.
   - `test_run_realtime_wraps_connection_error` — monkeypatch `websockets.connect` to raise `ConnectionError`, verify `APIError` is raised with chained cause.
   - `test_run_realtime_wraps_websocket_error` — monkeypatch `websockets.connect` to raise `websockets.exceptions.WebSocketException`, verify `APIError` is raised.
   - `test_run_realtime_happy_path_mock` — monkeypatch `websockets.connect` with an async context manager mock that simulates the full server event sequence (`session.created` -> `session.updated` -> `conversation.item.added` -> `response.output_text.delta` -> `response.done`), verify the returned text is correct.

   For the mock, create a simple async context manager class that yields a mock WebSocket with `send()` and `__aiter__()` methods that return pre-scripted server events.

5. **Run `make check`** from `packages/extract_text_from_audio/` to verify all tests pass and linting is clean.

## Production safety constraints (mandatory)

- **Database operations**: None.
- **Resource isolation**: WebSocket connections go to `api.openai.com` — no local ports or files used. No collision with production instance.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: This IS the shared infrastructure. It does not duplicate any existing functionality (there is no existing realtime runner in the codebase).
- **Correct libraries only**: `websockets>=14.0,<15` — well-established, actively maintained Python WebSocket library.
- **Correct file locations**: New file in `core/src/nl_processing/core/`, following naming conventions.
- **No regressions**: New file, no existing code modified (except adding a dependency to core's pyproject.toml).

## Error handling + correctness rules (mandatory)

- **All WebSocket and protocol errors** must be caught and wrapped as `APIError` with chained cause (`raise APIError(msg) from e`).
- **No empty catch blocks**.
- **`OPENAI_API_KEY`** accessed via `os.environ["OPENAI_API_KEY"]` — fails fast with `KeyError` if unset. No `os.getenv()` or `os.environ.get()` (banned by ruff.toml).
- **Server `error` events** must be parsed and raised as `APIError` with the server's error message.
- **Unexpected event types** should be ignored (the protocol may send events the runner doesn't care about, like `input_audio_buffer.*`). Only `error` events trigger failures.

## Zero legacy tolerance rule (mandatory)

- No legacy code to remove. This is a new module.
- No LangChain dependency — this runner is independent of the existing `build_translation_chain` in `core/prompts.py`.

## Acceptance criteria (testable)

1. `run_realtime_audio_session()` is importable from `nl_processing.core.realtime_runner`.
2. It accepts `audio_bytes`, `instructions`, and `model` parameters.
3. Missing `OPENAI_API_KEY` raises `KeyError` (fail-fast).
4. WebSocket connection errors are wrapped as `APIError`.
5. Server `error` events are wrapped as `APIError`.
6. Happy-path mock test returns expected text.
7. `realtime_runner.py` is under 200 lines.
8. `make check` passes from `packages/extract_text_from_audio/`.

## Verification / quality gates

- [ ] Unit tests cover: missing API key, connection errors, WebSocket errors, happy path with mocked server events
- [ ] `realtime_runner.py` under 200 lines
- [ ] Linters/formatters pass (`make check`)
- [ ] No `typing.Any`, relative imports, or banned APIs
- [ ] `APIError` wrapping verified for all failure modes
- [ ] `websockets` added to core `pyproject.toml`

## Edge cases

- Server sends `error` event before any response events — should raise `APIError` immediately.
- Server closes connection before `response.done` — `websockets.exceptions.ConnectionClosed` should be caught and wrapped as `APIError`.
- Empty text response from model (all deltas are empty strings) — should return empty string (the service layer in T4 will handle the `TargetLanguageNotFoundError` check).

## Notes / risks

- **RISK**: The Realtime API WebSocket protocol may have nuances not captured in documentation (event ordering, required acknowledgments). Mitigation: T4's integration tests with real API calls will validate the protocol implementation.
- **RISK**: `websockets` library API may differ between v13 and v14. Mitigation: Pin to `>=14.0,<15` and verify against v14 docs.
- The runner function is intentionally simple — one function, one session, one turn. This is not a general-purpose Realtime API client; it's scoped to the "submit audio, get text" use case.
