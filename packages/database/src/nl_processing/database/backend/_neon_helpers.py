"""Helper functions for NeonBackend operations."""


def infer_target_language(source_language: str) -> str:
    """Infer the other language in the nl/ru pair."""
    if source_language == "nl":
        return "ru"
    return "nl"
