"""SQL query templates for NeonBackend.

Table names are formatted from Language enum values (e.g., "nl", "ru") —
controlled strings, never user input. Lines with table name formatting
use ``# noqa: S608`` to acknowledge the ruff S608 check.
"""


def create_words_table(lang: str) -> str:
    # Table name from Language enum value, not user input  # noqa: S608
    return f"""
        CREATE TABLE IF NOT EXISTS words_{lang} (
            id SERIAL PRIMARY KEY,
            normalized_form VARCHAR NOT NULL UNIQUE,
            word_type VARCHAR NOT NULL
        )
    """  # noqa: S608


def create_translations_table(src: str, tgt: str) -> str:
    # Table names from Language enum values, not user input  # noqa: S608
    return f"""
        CREATE TABLE IF NOT EXISTS translations_{src}_{tgt} (
            id SERIAL PRIMARY KEY,
            source_word_id INTEGER NOT NULL REFERENCES words_{src}(id),
            target_word_id INTEGER NOT NULL REFERENCES words_{tgt}(id),
            UNIQUE(source_word_id, target_word_id)
        )
    """  # noqa: S608


CREATE_USER_WORDS = """
    CREATE TABLE IF NOT EXISTS user_words (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR NOT NULL,
        word_id INTEGER NOT NULL,
        language VARCHAR NOT NULL,
        added_at TIMESTAMP NOT NULL DEFAULT NOW(),
        UNIQUE(user_id, word_id, language)
    )
"""


def create_exercise_scores_table(src: str, tgt: str, exercise_slug: str) -> str:
    # Table names from Language enum values, not user input  # noqa: S608
    return f"""
        CREATE TABLE IF NOT EXISTS user_word_exercise_scores_{src}_{tgt}_{exercise_slug} (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR NOT NULL,
            source_word_id INTEGER NOT NULL,
            score INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE(user_id, source_word_id)
        )
    """  # noqa: S608


def create_applied_events_table(src: str, tgt: str) -> str:
    # Table names from Language enum values, not user input  # noqa: S608
    return f"""
        CREATE TABLE IF NOT EXISTS applied_events_{src}_{tgt} (
            event_id VARCHAR PRIMARY KEY,
            applied_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """  # noqa: S608


def add_word_query(table: str) -> str:
    # Table name from Language enum value, not user input  # noqa: S608
    return f"""
        INSERT INTO words_{table} (normalized_form, word_type)
        VALUES ($1, $2)
        ON CONFLICT (normalized_form) DO NOTHING
        RETURNING id
    """  # noqa: S608


def get_word_query(table: str) -> str:
    # Table name from Language enum value, not user input  # noqa: S608
    return f"""
        SELECT id, normalized_form, word_type
        FROM words_{table}
        WHERE normalized_form = $1
    """  # noqa: S608


def add_translation_link_query(table: str) -> str:
    # Table name from Language enum value, not user input  # noqa: S608
    return f"""
        INSERT INTO translations_{table} (source_word_id, target_word_id)
        VALUES ($1, $2)
        ON CONFLICT DO NOTHING
    """  # noqa: S608


ADD_USER_WORD = """
    INSERT INTO user_words (user_id, word_id, language)
    VALUES ($1, $2, $3)
    ON CONFLICT DO NOTHING
"""


def get_user_words_query(
    language: str,
    source_lang: str,
    target_lang: str,
    word_type: str | None,
    limit: int | None,
    random_order: bool,
) -> str:
    # Table names from Language enum values, not user input  # noqa: S608
    query = f"""
        SELECT
            sw.id AS source_id,
            sw.normalized_form AS source_normalized_form,
            sw.word_type AS source_word_type,
            tw.id AS target_id,
            tw.normalized_form AS target_normalized_form,
            tw.word_type AS target_word_type
        FROM user_words uw
        JOIN words_{language} sw ON uw.word_id = sw.id
        JOIN translations_{source_lang}_{target_lang} t ON t.source_word_id = sw.id
        JOIN words_{target_lang} tw ON t.target_word_id = tw.id
        WHERE uw.user_id = $1 AND uw.language = $2
    """  # noqa: S608
    if word_type is not None:
        query += " AND sw.word_type = $3"
    if random_order:
        query += " ORDER BY RANDOM()"
    if limit is not None:
        param_idx = 4 if word_type is not None else 3
        query += f" LIMIT ${param_idx}"
    return query


def increment_score_query(table: str) -> str:
    # Table name from Language enum values, not user input  # noqa: S608
    return f"""
        INSERT INTO user_word_exercise_scores_{table}
            (user_id, source_word_id, score, updated_at)
        VALUES ($1, $2, $3, NOW())
        ON CONFLICT (user_id, source_word_id)
        DO UPDATE SET
            score = user_word_exercise_scores_{table}.score + $3,
            updated_at = NOW()
        RETURNING score
    """  # noqa: S608


def get_scores_query(table: str) -> str:
    # Table name from Language enum values, not user input  # noqa: S608
    return f"""
        SELECT source_word_id, score
        FROM user_word_exercise_scores_{table}
        WHERE user_id = $1
        AND source_word_id = ANY($2)
    """  # noqa: S608


def check_event_applied_query(table: str) -> str:
    # Table name from Language enum values, not user input  # noqa: S608
    return f"""
        SELECT 1 FROM {table}
        WHERE event_id = $1
    """  # noqa: S608


def mark_event_applied_query(table: str) -> str:
    # Table name from Language enum values, not user input  # noqa: S608
    return f"""
        INSERT INTO {table} (event_id)
        VALUES ($1)
        ON CONFLICT (event_id) DO NOTHING
    """  # noqa: S608
