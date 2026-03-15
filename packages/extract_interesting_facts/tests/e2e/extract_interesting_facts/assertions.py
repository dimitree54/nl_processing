LLM_CHATTER_PREFIXES = [
    "Конечно!",
    "Отлично!",
    "Sure,",
    "Of course",
    "Here is",
    "Certainly",
    "Надеюсь, это",
    "Рад помочь",
]


def assert_no_llm_chatter(result: str) -> None:
    """Assert that result doesn't start with common LLM chatter patterns."""
    for prefix in LLM_CHATTER_PREFIXES:
        assert not result.startswith(prefix), f"Output starts with LLM chatter: '{prefix}'"


def assert_contains_any(result: str, candidates: list[str], label: str) -> None:
    """Assert that result contains at least one of the candidate strings."""
    found = any(c in result for c in candidates)
    assert found, f"Expected {label} in result. Got:\n{result}"
