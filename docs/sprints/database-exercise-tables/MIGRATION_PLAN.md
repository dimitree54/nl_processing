# Migration Plan: Per-Exercise-Type Score Tables

Sprint: `2026-03-07_database-exercise-tables`

## Overview

This migration splits the single `user_word_exercise_scores_{src}_{tgt}` table into per-exercise-type tables and adds the `applied_events_{src}_{tgt}` table for idempotency tracking.

**This plan is a user-reviewed deliverable. DO NOT auto-execute against production.**

## Pre-migration

### 1. Backup

```sql
-- Create backup of the existing score table
CREATE TABLE user_word_exercise_scores_nl_ru_backup AS
SELECT * FROM user_word_exercise_scores_nl_ru;

-- Verify backup
SELECT COUNT(*) FROM user_word_exercise_scores_nl_ru_backup;
SELECT COUNT(*) FROM user_word_exercise_scores_nl_ru;
-- Both counts must match.
```

### 2. Identify exercise types in use

```sql
SELECT DISTINCT exercise_type
FROM user_word_exercise_scores_nl_ru
ORDER BY exercise_type;
```

Record the list. You will create one table per exercise type.

## Migration Steps

### Step 1: Create per-exercise-type tables

For each exercise type found in step 2 above (e.g., `flashcard`, `typing`, `multiple_choice`, `nl_to_ru`, `listen_and_type`):

```sql
CREATE TABLE IF NOT EXISTS user_word_exercise_scores_nl_ru_<exercise_slug> (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    source_word_id INTEGER NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, source_word_id)
);
```

Example for three types:

```sql
CREATE TABLE IF NOT EXISTS user_word_exercise_scores_nl_ru_nl_to_ru (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    source_word_id INTEGER NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, source_word_id)
);

CREATE TABLE IF NOT EXISTS user_word_exercise_scores_nl_ru_multiple_choice (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    source_word_id INTEGER NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, source_word_id)
);

CREATE TABLE IF NOT EXISTS user_word_exercise_scores_nl_ru_listen_and_type (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    source_word_id INTEGER NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, source_word_id)
);
```

### Step 2: Migrate data from old table to new tables

For each exercise type:

```sql
INSERT INTO user_word_exercise_scores_nl_ru_<exercise_slug>
    (user_id, source_word_id, score, updated_at)
SELECT user_id, source_word_id, score, updated_at
FROM user_word_exercise_scores_nl_ru
WHERE exercise_type = '<exercise_slug>'
ON CONFLICT (user_id, source_word_id) DO UPDATE SET
    score = EXCLUDED.score,
    updated_at = EXCLUDED.updated_at;
```

### Step 3: Create applied_events table

```sql
CREATE TABLE IF NOT EXISTS applied_events_nl_ru (
    event_id VARCHAR PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### Step 4: Validate migration

```sql
-- For each exercise type, verify row counts match
SELECT COUNT(*) FROM user_word_exercise_scores_nl_ru WHERE exercise_type = '<slug>';
SELECT COUNT(*) FROM user_word_exercise_scores_nl_ru_<slug>;
-- Counts must match for each exercise type.

-- Verify total rows across new tables equals total rows in old table
SELECT SUM(cnt) FROM (
    SELECT COUNT(*) AS cnt FROM user_word_exercise_scores_nl_ru_nl_to_ru
    UNION ALL
    SELECT COUNT(*) FROM user_word_exercise_scores_nl_ru_multiple_choice
    UNION ALL
    SELECT COUNT(*) FROM user_word_exercise_scores_nl_ru_listen_and_type
) sub;

SELECT COUNT(*) FROM user_word_exercise_scores_nl_ru;
-- Both totals must match.
```

### Step 5: Deploy new code

Deploy the updated application code (this sprint's changes). The new code reads/writes per-exercise-type tables.

### Step 6: Drop old table (after validation)

**Only after confirming the new code is working correctly in production:**

```sql
DROP TABLE user_word_exercise_scores_nl_ru;
```

## Rollback

If issues are found after migration:

### Quick rollback (before old table is dropped)

1. Revert to old application code.
2. Old table still exists with original data — application works immediately.

### Full rollback (after old table is dropped)

1. Restore from backup:
   ```sql
   CREATE TABLE user_word_exercise_scores_nl_ru AS
   SELECT * FROM user_word_exercise_scores_nl_ru_backup;
   ```
2. Revert to old application code.
3. Drop per-exercise-type tables:
   ```sql
   DROP TABLE IF EXISTS user_word_exercise_scores_nl_ru_nl_to_ru;
   DROP TABLE IF EXISTS user_word_exercise_scores_nl_ru_multiple_choice;
   DROP TABLE IF EXISTS user_word_exercise_scores_nl_ru_listen_and_type;
   DROP TABLE IF EXISTS applied_events_nl_ru;
   ```

## Downtime

- **Expected downtime**: None. Tables can be created and data migrated while the old code is still running (old code reads/writes the old table). Deploy new code only after migration is complete.
- **Risk window**: Between data migration and code deploy, any new scores written to the old table will not be in the new tables. To minimize: migrate data, then immediately deploy new code.

## Post-migration cleanup

After confirming production is stable (recommend 24–48 hours):

```sql
DROP TABLE IF EXISTS user_word_exercise_scores_nl_ru_backup;
```
