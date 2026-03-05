# Neon PostgreSQL Setup

## Project

- **Neon project name:** nl-processing
- **Neon project ID:** polished-morning-72742670
- **Region:** aws-us-east-2
- **PostgreSQL version:** 17

## Branches

| Branch | Purpose | Neon Branch ID |
|--------|---------|----------------|
| `main` | Production data — never touched by tests | `br-red-poetry-ajpbtt2o` |
| `dev` | Development + all automated tests — freely wiped | `br-tiny-meadow-aj7f50pk` |

## Connection Strings

Connection strings are stored in **Doppler** (never committed to git):

| Doppler Config | Neon Branch | Doppler Secret |
|----------------|-------------|----------------|
| `dev` | `dev` | `DATABASE_URL` |
| `prd` | `main` | `DATABASE_URL` |

To retrieve a connection string manually:

```bash
neonctl connection-string --project-id polished-morning-72742670 --branch dev
neonctl connection-string --project-id polished-morning-72742670 --branch main
```

## Environment Variables

| Variable | Description | Managed By |
|----------|-------------|------------|
| `DATABASE_URL` | PostgreSQL connection string (per environment) | Doppler |

## Usage

All commands requiring database access run via Doppler:

```bash
doppler run -- uv run pytest tests/integration
doppler run -- uv run pytest tests/e2e
doppler run -- make check
```

## Credential Rotation

1. Reset password in Neon console or via `neonctl`
2. Get new connection string: `neonctl connection-string --project-id polished-morning-72742670 --branch <branch>`
3. Update in Doppler: `doppler secrets set DATABASE_URL="<new-url>" --config <dev|prd>`

## Rules

- **Dev database** (`dev` branch): Ephemeral — tests freely create/drop/reset tables
- **Production database** (`main` branch): Stable — never touched by automated tests
- `create_tables()` uses `IF NOT EXISTS` — safe in any environment
- `drop_all_tables()` and `reset_database()` should ONLY run against the dev database
