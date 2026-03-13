"""DDL and query constants for detailed word cache SQLite store."""

CREATE_DETAILED_WORDS_TABLE = """
    CREATE TABLE IF NOT EXISTS cached_detailed_words (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_word TEXT NOT NULL,
        word_type TEXT NOT NULL,
        schema_key TEXT NOT NULL,
        schema_version INTEGER NOT NULL,
        payload TEXT NOT NULL,
        cached_at TEXT NOT NULL,
        UNIQUE(source_word, word_type)
    )
"""

INSERT_OR_REPLACE_DETAILED = """
    INSERT OR REPLACE INTO cached_detailed_words
    (source_word, word_type, schema_key, schema_version, payload, cached_at)
    VALUES (?, ?, ?, ?, ?, ?)
"""

SELECT_DETAILED = """
    SELECT source_word, word_type, schema_key, schema_version, payload
    FROM cached_detailed_words
    WHERE source_word = ? AND word_type = ?
"""

DELETE_DETAILED = """
    DELETE FROM cached_detailed_words
    WHERE source_word = ? AND word_type = ?
"""
