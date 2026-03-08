"""DDL and query constants for the local SQLite cache store."""

DDL_CACHED_WORD_PAIRS = """
CREATE TABLE IF NOT EXISTS cached_word_pairs (
    source_word_id INTEGER PRIMARY KEY,
    source_normalized_form TEXT NOT NULL,
    source_word_type TEXT NOT NULL,
    target_word_id INTEGER NOT NULL,
    target_normalized_form TEXT NOT NULL,
    target_word_type TEXT NOT NULL
)"""

DDL_CACHED_SCORES = """
CREATE TABLE IF NOT EXISTS cached_scores (
    source_word_id INTEGER NOT NULL,
    exercise_type TEXT NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (source_word_id, exercise_type)
)"""

DDL_PENDING_SCORE_EVENTS = """
CREATE TABLE IF NOT EXISTS pending_score_events (
    event_id TEXT PRIMARY KEY,
    source_word_id INTEGER NOT NULL,
    exercise_type TEXT NOT NULL,
    delta INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    flushed_at TEXT,
    last_error TEXT
)"""

DDL_CACHE_METADATA = """
CREATE TABLE IF NOT EXISTS cache_metadata (
    id INTEGER PRIMARY KEY DEFAULT 1,
    exercise_types TEXT NOT NULL,
    schema_version INTEGER NOT NULL DEFAULT 1,
    last_refresh_started_at TEXT,
    last_refresh_completed_at TEXT,
    last_flush_completed_at TEXT,
    last_error TEXT
)"""

ALL_DDL = [DDL_CACHED_WORD_PAIRS, DDL_CACHED_SCORES, DDL_PENDING_SCORE_EVENTS, DDL_CACHE_METADATA]

UPSERT_SCORE = (
    "INSERT INTO cached_scores (source_word_id, exercise_type, score, updated_at) VALUES (?, ?, ?, ?)"
    " ON CONFLICT(source_word_id, exercise_type) DO UPDATE SET score = score + ?, updated_at = ?"
)

INSERT_PENDING_EVENT = (
    "INSERT INTO pending_score_events (event_id, source_word_id, exercise_type, delta, created_at)"
    " VALUES (?, ?, ?, ?, ?)"
)

INSERT_WORD_PAIR = "INSERT INTO cached_word_pairs VALUES (?, ?, ?, ?, ?, ?)"

INSERT_SCORE = "INSERT INTO cached_scores (source_word_id, exercise_type, score, updated_at) VALUES (?, ?, ?, ?)"
