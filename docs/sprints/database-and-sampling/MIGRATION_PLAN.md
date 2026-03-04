# Migration Plan — database module tables

## Overview

The `database` module creates several PostgreSQL tables in Neon. This document describes the tables, how to create them, and how to manage them across environments.

## Tables Created

### Per-language word tables

- `words_nl` — Dutch words
- `words_ru` — Russian words

Schema: `id SERIAL PK, normalized_form VARCHAR UNIQUE NOT NULL, word_type VARCHAR NOT NULL`

### Per-language-pair translation link tables

- `translations_nl_ru` — NL→RU translation links

Schema: `id SERIAL PK, source_word_id INT FK→words_nl, target_word_id INT FK→words_ru, UNIQUE(source_word_id, target_word_id)`

### User word list table

- `user_words` — user-word associations

Schema: `id SERIAL PK, user_id VARCHAR NOT NULL, word_id INT NOT NULL, language VARCHAR NOT NULL, added_at TIMESTAMP NOT NULL DEFAULT NOW(), UNIQUE(user_id, word_id, language)`

### Per-language-pair exercise score tables

- `user_word_exercise_scores_nl_ru` — per-user per-exercise scores

Schema: `id SERIAL PK, user_id VARCHAR NOT NULL, source_word_id INT FK→words_nl, exercise_type VARCHAR NOT NULL, score INT NOT NULL DEFAULT 0, updated_at TIMESTAMP NOT NULL DEFAULT NOW(), UNIQUE(user_id, source_word_id, exercise_type)`

## Creating Tables

Tables are created via `DatabaseService.create_tables()`:

```python
from nl_processing.database.service import DatabaseService
await DatabaseService.create_tables()
```

This method uses `CREATE TABLE IF NOT EXISTS` — safe to run in any environment without risk of data loss.

## Environment Strategy

| Environment | Database | Action |
|---|---|---|
| `dev` | `nl_processing_dev` | Tests freely create/drop tables. `reset_database()` and `drop_all_tables()` used in test setup/teardown. |
| `stg` | `nl_processing_stg` | Run `create_tables()` once manually to set up. Never drop tables automatically. |
| `prd` | `nl_processing_prd` | Run `create_tables()` once manually to set up. Never drop tables automatically. |

## Production Deployment Steps

1. Ensure `DATABASE_URL` in Doppler `prd` environment points to the production Neon database.
2. Run `create_tables()` once:
   ```bash
   doppler run -c prd -- uv run python -c "
   import asyncio
   from nl_processing.database.service import DatabaseService
   asyncio.run(DatabaseService.create_tables())
   print('Tables created successfully')
   "
   ```
3. Verify tables exist by connecting to Neon console and checking `information_schema.tables`.
4. The module is ready for use.

## Rollback

To remove all tables (IRREVERSIBLE):

```python
from nl_processing.database.testing import drop_all_tables
await drop_all_tables(["nl", "ru"], [("nl", "ru")])
```

**WARNING**: This drops ALL data. Only use in dev environment or after explicit backup.

## Backup Before Migration

Before creating tables in production for the first time:
- No existing data to back up (greenfield)
- For future schema changes: take a Neon database snapshot via Neon console before any DDL changes

## Validation Queries

After creating tables, verify:

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

Expected tables: `translations_nl_ru`, `user_word_exercise_scores_nl_ru`, `user_words`, `words_nl`, `words_ru`
