"""SQL query templates for delete operations.

Table names are formatted from Language enum values (e.g., "nl", "ru") —
controlled strings, never user input. Lines with table name formatting
use ``# noqa: S608`` to acknowledge the ruff S608 check.
"""


def check_user_word_exists_query(language: str) -> str:
    """Check if a source word belongs to user's vocabulary."""
    # noqa: S608
    return f"""
        SELECT 1 FROM user_words uw
        JOIN words_{language} sw ON uw.word_id = sw.id
        WHERE uw.user_id = $1 AND sw.id = $2 AND uw.language = $3
    """  # noqa: S608


def delete_user_word_query() -> str:
    """Delete user's membership row for a specific word."""
    return """
        DELETE FROM user_words
        WHERE user_id = $1 AND word_id = $2 AND language = $3
    """


def delete_user_exercise_score_query(table: str) -> str:
    """Delete user's exercise score for a specific word."""
    # noqa: S608
    return f"""
        DELETE FROM user_word_exercise_scores_{table}
        WHERE user_id = $1 AND source_word_id = $2
    """  # noqa: S608
