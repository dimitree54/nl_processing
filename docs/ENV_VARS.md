# Environment Variables — nl_processing

All environment variables are managed via **Doppler CLI**.

- **Doppler project:** `nl_processing`
- **Environments:** `dev`, `stg`, `prd`

## Required Variables

| Variable | Type | Description | Set by |
|---|---|---|---|
| `OPENAI_API_KEY` | Secret | OpenAI API authentication key for all LLM calls | Developer (via Doppler) |

## Usage

All commands requiring env vars must run with `doppler run --`:

```bash
doppler run -- uv run pytest -n auto tests/unit
doppler run -- make check
```

## Adding New Variables

1. Set in **all three environments** (`dev`, `stg`, `prd`):
   ```bash
   doppler secrets set -p nl_processing -c dev KEY=value
   doppler secrets set -p nl_processing -c stg KEY=value
   doppler secrets set -p nl_processing -c prd KEY=value
   ```
2. Update this file with the new variable.
3. If the variable is a secret (API key, token, password), ask the developer to set it — do not set autonomously.
